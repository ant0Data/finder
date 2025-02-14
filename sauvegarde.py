import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import json
import requests
from datetime import datetime, timedelta
import time
from tqdm import tqdm
import numpy as np
import re
import os
import openai
import fitz  # PyMuPDF pour lire les PDF
import webbrowser
from dotenv import load_dotenv
from openai import ChatCompletion
import random 

# Définition de la clé API au niveau du module (ici dans secrets.toml)
openai.api_key = st.secrets["API_KEY_IA"]

load_dotenv()  # Charger les variables d'environnement
# api_key_ia = st.secrets["API_KEY_IA"]  # Récupérer la clé API IAG
api_key_ft = st.secrets["API_KEY_FT"]  # récupérer la clé API France Travail
client_id_ft = st.secrets["CLIENT_ID_FT"]  # récupérer l'identifiant France Travail

# Configuration de l'application (définit le titre et la mise en page)
st.set_page_config(page_title="Finder", layout="wide")

def upload_cv():
    """Permet à l'utilisateur d'uploader son CV au format PDF."""
    return st.file_uploader("Uploadez votre CV en PDF", type=["pdf"], key="cv_uploader")


def extract_text_from_pdf(pdf_file):
    """Extrait le texte d'un fichier PDF."""
    try:
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text("text") + "\n"
        return text.strip()
    except Exception as e:
        st.error(f"Erreur lors de la lecture du PDF : {e}")
        return None


def get_keywords_from_cv(cv_file):
    """Analyse un CV pour en extraire des mots-clés."""
    if cv_file is None:
        st.error("Aucun fichier CV détecté.")
        return None, None, None

    cv_text = extract_text_from_pdf(cv_file)
    if not cv_text:
        st.error("Impossible d'extraire le texte du CV.")
        return None, None, None

    # Prompts mis à jour avec des consignes strictes
    keywords_domaine_prompt = "Donne uniquement ces deux mots exacts et dans cet ordre, séparés par une virgule : Data, Développement"
    keywords_intitule_prompt = f"""
    Identifie entre 3 et 8 intitulés de métiers qui correspondent au texte ci-dessous.
    Donne uniquement les intitulés séparés par des virgules, sans explication, sans texte supplémentaire.
    Texte : {cv_text}
    """
    analysis_prompt = f"""
    Retourne uniquement un objet JSON contenant les éléments suivants, ne retourne que ce qui est explicitement écrit dans le cv :
    {{
      "soft_skills": ["liste des soft skills"],
      "hard_skills": ["liste des hard skills"],
      "savoir_faire": ["liste des savoir-faire"],
      "savoir_etre": ["liste des savoir-être"]
    }}
    Ne donne aucune explication supplémentaire.
    Texte : {cv_text}
    """

    try:
        model = "gpt-4o-mini"
        # Envoi des requêtes à l'API OpenAI
        keywords_domaine_response = openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "user", "content": keywords_domaine_prompt}],
        )
        keywords_intitule_response = openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "user", "content": keywords_intitule_prompt}],
        )
        analysis_response = openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "user", "content": analysis_prompt}],
        )

        # Extraction des réponses
        keywords_domaine_raw = keywords_domaine_response["choices"][0]["message"]["content"].strip()
        keywords_domaine = [kw.strip() for kw in keywords_domaine_raw.split(",") if kw.strip()]

        keywords_intitule_raw = keywords_intitule_response["choices"][0]["message"]["content"].strip()
        keywords_intitule = [kw.strip() for kw in keywords_intitule_raw.split(",") if kw.strip()]

        analysis_raw = analysis_response["choices"][0]["message"]["content"].strip()
        if not analysis_raw:
            st.error("La réponse de l'IA est vide.")
            return None, None, None

        # Nettoyage de la réponse JSON
        analysis_clean = re.sub(r"^```(?:json)?\s*", "", analysis_raw)
        analysis_clean = re.sub(r"\s*```$", "", analysis_clean)
        analysis_clean = re.sub(r"<[^>]*>", "", analysis_clean)

        try:
            analysis = json.loads(analysis_clean)
        except json.JSONDecodeError as e:
            st.error(f"Erreur de décodage JSON : {str(e)}. Réponse nettoyée : {analysis_clean}")
            return None, None, None

        # Vérifications assouplies
        if keywords_intitule and "soft_skills" in analysis and "hard_skills" in analysis:
            return keywords_domaine, keywords_intitule, analysis
        else:
            if len(keywords_intitule) < 3:
                st.error("L'analyse n'a pas identifié suffisamment d'intitulés de métiers.")
            if "soft_skills" not in analysis or "hard_skills" not in analysis:
                st.error("L'analyse n'a pas retourné les compétences attendues.")
            return None, None, None

    except Exception as e:
        st.error(f"Erreur lors de la communication avec l'IA : {str(e)}")
        return None, None, None


def get_job_offers(mot_cle):
    """Récupère les offres d'emploi depuis France Travail."""
    if not mot_cle:
        st.error("Aucun mot-clé fourni pour la recherche d'emploi.")
        return None

    start_time = time.time()

    # Identifiants d'accès
    client_id = client_id_ft  #  Remplacement de la valeur statique
    client_secret = api_key_ft  #  Remplacement de la valeur statique

    auth_url = "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=%2Fpartenaire"
    auth_data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "api_offresdemploiv2 o2dsoffre",
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    auth_response = requests.post(auth_url, data=auth_data, headers=headers)

    if auth_response.status_code == 200:
        access_token = auth_response.json().get("access_token")
        print("Authentification réussie. Token obtenu.")
    else:
        st.error(f"Erreur d'authentification : {auth_response.status_code}")
        return None

    search_url = "https://api.emploi-store.fr/partenaire/offresdemploi/v2/offres/search"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    all_offers = []
    start = 0
    step = 50  # Nombre d'offres par page
    max_results = 3000  # Limite de récupération

    progress_bar = tqdm(total=max_results // step, desc="Récupération des offres", unit="page")

    while start < max_results:
        params = {
            "motsCles": mot_cle,
            "range": f"{start}-{min(start + step - 1, max_results - 1)}",
        }
        response = requests.get(search_url, headers=headers, params=params, timeout=90)
        if response.status_code in [200, 206]:
            data = response.json()
            offers = data.get("resultats", [])
            all_offers.extend(offers)
            if len(offers) < step:
                break
            start += step
            progress_bar.update(1)
        else:
            st.error(f"Erreur lors de la requête : {response.status_code}")
            break

    progress_bar.close()
    print(f"{len(all_offers)} offres récupérées.")

    if all_offers:
        df = pd.json_normalize(all_offers)
        df.columns = df.columns.str.replace(".", "_")
        if "dateCreation" in df.columns:
            df["dateCreation"] = pd.to_datetime(df["dateCreation"], utc=True).dt.tz_convert(None)
            date_limit = datetime.utcnow() - timedelta(days=10)
            df_recent = df[df["dateCreation"] >= date_limit]
            print(
                f"Données enregistrées : {len(df)} offres totales, {len(df_recent)} des 10 derniers jours."
            )
            elapsed_time = time.time() - start_time
            print(f"Temps d'exécution total : {elapsed_time:.2f} secondes")
            return df_recent
    return None


def departement(text):
    """Convertit un code de département en nom."""
    text = str(text).strip()
    if text.lower() == "france":
        return "France entière"
    match = re.match(r"^(2A|2B|\d{1,3})", text)
    if match:
        numero = match.group()
    else:
        return text
    departements = {
        "01": "Ain",
        "02": "Aisne",
        "03": "Allier",
        "04": "Alpes-de-Haute-Provence",
        "05": "Hautes-Alpes",
        "06": "Alpes-Maritimes",
        "07": "Ardèche",
        "08": "Ardennes",
        "09": "Ariège",
        "10": "Aube",
        "11": "Aude",
        "12": "Aveyron",
        "13": "Bouches-du-Rhône",
        "14": "Calvados",
        "15": "Cantal",
        "16": "Charente",
        "17": "Charente-Maritime",
        "18": "Cher",
        "19": "Corrèze",
        "2A": "Corse-du-Sud",
        "2B": "Haute-Corse",
        "21": "Côte-d'Or",
        "22": "Côtes-d'Armor",
        "23": "Creuse",
        "24": "Dordogne",
        "25": "Doubs",
        "26": "Drôme",
        "27": "Eure",
        "28": "Eure-et-Loir",
        "29": "Finistère",
        "30": "Gard",
        "31": "Haute-Garonne",
        "32": "Gers",
        "33": "Gironde",
        "34": "Hérault",
        "35": "Ille-et-Vilaine",
        "36": "Indre",
        "37": "Indre-et-Loire",
        "38": "Isère",
        "39": "Jura",
        "40": "Landes",
        "41": "Loir-et-Cher",
        "42": "Loire",
        "43": "Haute-Loire",
        "44": "Loire-Atlantique",
        "45": "Loiret",
        "46": "Lot",
        "47": "Lot-et-Garonne",
        "48": "Lozère",
        "49": "Maine-et-Loire",
        "50": "Manche",
        "51": "Marne",
        "52": "Haute-Marne",
        "53": "Mayenne",
        "54": "Meurthe-et-Moselle",
        "55": "Meuse",
        "56": "Morbihan",
        "57": "Moselle",
        "58": "Nièvre",
        "59": "Nord",
        "60": "Oise",
        "61": "Orne",
        "62": "Pas-de-Calais",
        "63": "Puy-de-Dôme",
        "64": "Pyrénées-Atlantiques",
        "65": "Hautes-Pyrénées",
        "66": "Pyrénées-Orientales",
        "67": "Bas-Rhin",
        "68": "Haut-Rhin",
        "69": "Rhône",
        "70": "Haute-Saône",
        "71": "Saône-et-Loire",
        "72": "Sarthe",
        "73": "Savoie",
        "74": "Haute-Savoie",
        "75": "Paris",
        "76": "Seine-Maritime",
        "77": "Seine-et-Marne",
        "78": "Yvelines",
        "79": "Deux-Sèvres",
        "80": "Somme",
        "81": "Tarn",
        "82": "Tarn-et-Garonne",
        "83": "Var",
        "84": "Vaucluse",
        "85": "Vendée",
        "86": "Vienne",
        "87": "Haute-Vienne",
        "88": "Vosges",
        "89": "Yonne",
        "90": "Territoire de Belfort",
        "91": "Essonne",
        "92": "Hauts-de-Seine",
        "93": "Seine-Saint-Denis",
        "94": "Val-de-Marne",
        "95": "Val-d'Oise",
        "971": "Guadeloupe",
        "972": "Martinique",
        "973": "Guyane",
        "974": "La Réunion",
        "976": "Mayotte",
    }
    if numero in departements:
        return f"{numero} - {departements[numero]}"
    else:
        return "Inconnu"


def process_data(df_recent):
    if df_recent is not None and not df_recent.empty:
        df_clean = df_recent.drop(
            [
                "competences",
                "dureeTravailLibelle",
                "dureeTravailLibelleConverti",
                "deplacementCode",
                "deplacementLibelle",
                "qualificationCode",
                "qualificationLibelle",
                "codeNAF",
                "secteurActivite",
                "secteurActiviteLibelle",
                "offresManqueCandidats",
                "entreprise_nom",
                "salaire_libelle",
                "salaire_complement1",
                "salaire_complement2",
                "contact_nom",
                "contact_coordonnees1",
                "contact_courriel",
                "contexteTravail_conditionsExercice",
                "formations",
                "entreprise_logo",
                "contact_urlPostulation",
                "langues",
                "qualitesProfessionnelles",
                "salaire_commentaire",
                "entreprise_url",
                "permis",
                "experienceCommentaire",
                "contact_coordonnees2",
                "contact_coordonnees3",
                "agence_courriel",
                "complementExercice",
                "nombrePostes",
                "origineOffre_partenaires",
                "lieuTravail_commune",
                "dateActualisation",
                "origineOffre_origine",
                "entreprise_entrepriseAdaptee",
                "natureContrat",
            ],
            axis=1,
            errors="ignore",
        )
        print("Données nettoyées avec succès.")
        rome_counts = df_clean["romeLibelle"].value_counts(normalize=True) * 100
        rome_above_3 = rome_counts[np.round(rome_counts, 2) > 3].index
        df_final = df_clean[df_clean["romeLibelle"].isin(rome_above_3)]
        df_final["departement"] = df_final["lieuTravail_libelle"].apply(departement)
        return df_final
    else:
        print("Aucune offre récente récupérée, nettoyage impossible.")
        return None


def filter_offers(df_final, selected_departement=None, selected_typeContrat=None, selected_intitule=None):
    filtered_df = df_final.copy()
    if selected_departement:
        filtered_df = filtered_df[filtered_df["departement"].isin(selected_departement)]
    if selected_typeContrat:
        filtered_df = filtered_df[filtered_df["typeContrat"].isin(selected_typeContrat)]
    if selected_intitule:
        filtered_df = filtered_df[filtered_df["appellationlibelle"].isin(selected_intitule)]
    return filtered_df


def display_dashboard(filtered_df):
    """
    Affiche un tableau de bord interactif avec des filtres interdépendants.
    Les options des filtres (Département, Type de contrat, Intitulé du poste)
    sont calculées à partir du DataFrame complet des offres (base_df).
    """
    st.subheader("Tableau de bord des offres d'emploi")
    # On récupère le DataFrame complet stocké en session (ou celui passé en argument)
    base_df = st.session_state.get("df_offers", filtered_df).copy()

    # Si la colonne "departement" n'existe pas, on la crée à partir de "lieuTravail_libelle"
    if "departement" not in base_df.columns:
        if "lieuTravail_libelle" in base_df.columns:
            base_df["departement"] = base_df["lieuTravail_libelle"].apply(departement)
        else:
            base_df["departement"] = ""

        selected_departement = st.session_state.get("selected_departement", [])
    selected_typeContrat = st.session_state.get("selected_typeContrat", [])
    selected_intitule = st.session_state.get("selected_intitule", [])

    # Conversion forcée en listes si ce sont des chaînes de caractères
    if isinstance(selected_departement, str):
        selected_departement = [selected_departement]
    if isinstance(selected_typeContrat, str):
        selected_typeContrat = [selected_typeContrat]
    if isinstance(selected_intitule, str):
        selected_intitule = [selected_intitule]


    # Calcul des options pour "Département"
    if not selected_typeContrat and not selected_intitule:
        departement_options = sorted(base_df["departement"].unique())
    else:
        df_dept = base_df.copy()
        if selected_typeContrat:
            df_dept = df_dept[df_dept["typeContrat"].isin(selected_typeContrat)]
        if selected_intitule:
            df_dept = df_dept[df_dept["appellationlibelle"].isin(selected_intitule)]
        if df_dept.empty:
            departement_options = sorted(base_df["departement"].unique())
        else:
            departement_options = sorted(df_dept["departement"].unique())

    # Calcul des options pour "Type de contrat"
    if not selected_departement and not selected_intitule:
        type_contrat_options = (
            sorted(base_df["typeContrat"].unique())
            if "typeContrat" in base_df.columns
            else []
        )
    else:
        df_contrat = base_df.copy()
        if selected_departement:
            df_contrat = df_contrat[df_contrat["departement"].isin(selected_departement)]
        if selected_intitule:
            df_contrat = df_contrat[df_contrat["appellationlibelle"].isin(selected_intitule)]
        if df_contrat.empty and "typeContrat" in base_df.columns:
            type_contrat_options = sorted(base_df["typeContrat"].unique())
        else:
            type_contrat_options = sorted(df_contrat["typeContrat"].unique())

    # Calcul des options pour "Intitulé du poste"
    if not selected_departement and not selected_typeContrat:
        intitule_options = (
            sorted(base_df["appellationlibelle"].unique())
            if "appellationlibelle" in base_df.columns
            else []
        )
    else:
        df_intitule = base_df.copy()
        if selected_departement:
            df_intitule = df_intitule[df_intitule["departement"].isin(selected_departement)]
        if selected_typeContrat:
            df_intitule = df_intitule[df_intitule["typeContrat"].isin(selected_typeContrat)]
        if df_intitule.empty and "appellationlibelle" in base_df.columns:
            intitule_options = sorted(base_df["appellationlibelle"].unique())
        else:
            intitule_options = sorted(df_intitule["appellationlibelle"].unique())

    # Filtrer les valeurs par défaut pour s'assurer qu'elles se trouvent dans les options
    default_dept = [d for d in selected_departement if d in departement_options]
    default_contrat = [t for t in selected_typeContrat if t in type_contrat_options]
    default_intitule = [i for i in selected_intitule if i in intitule_options]

    # Création des colonnes pour afficher les filtres
    col1, col2, col3 = st.columns(3)
    with col1:
        selected_departement = st.multiselect(
            "Département",
            options=departement_options,
            default=default_dept,
            key="selected_departement",
        )
    with col2:
        selected_typeContrat = st.multiselect(
            "Type de contrat",
            options=type_contrat_options,
            default=default_contrat,
            key="selected_typeContrat",
        )
    with col3:
        selected_intitule = st.multiselect(
            "Intitulé du poste",
            options=intitule_options,
            default=default_intitule,
            key="selected_intitule",
        )

    # Application des filtres sur le DataFrame de base
    df_filtered = base_df.copy()
    if selected_departement:
        df_filtered = df_filtered[df_filtered["departement"].isin(selected_departement)]
    if selected_typeContrat:
        df_filtered = df_filtered[df_filtered["typeContrat"].isin(selected_typeContrat)]
    if selected_intitule:
        df_filtered = df_filtered[df_filtered["appellationlibelle"].isin(selected_intitule)]

    if st.button("Voir les offres"):
        st.session_state["filtered_df"] = df_filtered
        st.session_state["page"] = "offers"
        st.rerun()

    st.write("Graphiques interactifs ici...")


def generate_cover_letter(analysis, job_offer_details):
    prompt = f"""Tu es un expert en rédaction de lettres de motivation sur mesure, spécialisées pour des profils professionnels. Ta mission est de rédiger une lettre de motivation convaincante et personnalisée, en respectant les consignes suivantes :

- La lettre doit être structurée en plusieurs paragraphes clairs et bien articulés.
- Elle doit refléter une compréhension approfondie du poste et des attentes de l'employeur.
- Elle doit valoriser les expériences, compétences et projets du candidat en lien avec l'offre d'emploi sans déclarer des compétences ou des expériences qui ne sont pas explicitement indiquées dans le cv:
il t'es strictment interdit de mentionner une experience professionnelle ou une compétence technique qui n'apparait pas dans le fichier analysis (analyse du cv).
- Tu ne peux pas extrapoler des expériences ou compétences dans le but de correspondre mieux à l'offre d'emploi. Interdit de mentionner une expérience qui n'apparaît pas dans le cv. Idem pour les compétences techniques.
- Tu dois respecter scrupuleusement mes intitulés de formation et de diplômes, il est strictment interdit de les déformer pour les faire correspondre à l'offre d'emploi.
- Le ton doit être professionnel et enthousiaste, avec des formulations précises et pertinentes.
- La lettre ne doit pas dépasser une page.
- Conforme toi strictment aux restrictions que je t'ai indiquées.

### Informations disponibles :

1. **Analyse du CV** :
   {analysis}

2. **Détails de l'offre d'emploi** :
   {job_offer_details}

### Exemple de structure à suivre :

1. **Introduction** : Débuter par une accroche engageante, en mentionnant directement le poste et les motivations pour celui-ci.
2. **Profil du candidat** : Présenter les expériences réelles, celles qui apparaissent explicitement dans le cv, compétences et projets clés qui répondent aux exigences du poste.
3. **Apport pour l'entreprise** : Expliquer comment le candidat peut contribuer à la mission et aux objectifs de l'organisation.
4. **Conclusion** : Proposer un entretien, remercier pour l'attention portée à la candidature, et exprimer une motivation claire.

### Format attendu :

La sortie doit être une lettre de motivation complète, prête à être utilisée, avec un format adapté aux standards professionnels.

Commence chaque lettre par une phrase engageante et personnalisée, et termine par une formule de politesse classique adaptée au contexte.

    """
    try:
        model = "gpt-4o-mini"
        response = openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        cover_letter = response.choices[0].message.content.strip()
        st.download_button(
            label="Télécharger la lettre de motivation",
            data=cover_letter,
            file_name="lettre_de_motivation.txt",
            mime="text/plain",
        )
        return cover_letter
    except Exception as e:
        st.error(f"Erreur lors de la génération de la lettre de motivation : {str(e)}")
        return None


def display_offers(filtered_df):
    st.subheader("Offres d'emploi correspondantes")
    if "applied_jobs" not in st.session_state:
        st.session_state["applied_jobs"] = set()
    if st.button("Retour au tableau de bord"):
        st.session_state["page"] = "dashboard"
        st.rerun()
    for _, row in filtered_df.iterrows():
        offer_key = row["id"]
        is_applied = offer_key in st.session_state["applied_jobs"]
        text_color = "#007BFF" if is_applied else "#000"
        container_background = "#d1ecf1" if is_applied else "#fff"
        with st.container():
            st.markdown(
                f"""
                <div style="background-color: {container_background}; padding: 10px; border-radius: 5px;">
                    <strong style="color: {text_color};">
                        N°{row['id']} - {row['intitule']} | {row['typeContrat']} | {row['lieuTravail_libelle']}
                    </strong>
                </div>
                """,
                unsafe_allow_html=True,
            )
            with st.expander("Voir les détails"):
                st.write(f"**Description :** {row['description']}")
                if st.button("Générer une lettre de motivation", key=f"lm_{offer_key}"):
                    cv_analysis = st.session_state.get("cv_analysis")
                    if not cv_analysis:
                        st.error("L'analyse du CV n'a pas été réalisée.")
                    else:
                        generate_cover_letter(cv_analysis, row["description"])
                # Bouton "Postuler"
                if st.button("Postuler", key=f"postuler_{offer_key}"):
                    url = row.get("origineOffre_urlOrigine", "")
                    if url:
                        webbrowser.open_new_tab(url)  # Ouvre l'URL dans un nouvel onglet
                        st.session_state["applied_jobs"].add(offer_key)  # Marque l'offre comme postulée
                        st.rerun()  # Rafraîchit l'interface pour appliquer les changements


def clear_intitule():
    st.session_state.selected_intitule = None  # Effacer la sélection dans la rubrique intitulé


def clear_domaine():
    st.session_state.selected_domaine = None  # Effacer la sélection dans la rubrique domaine


def display_advice():
    html_code = """
    <style>
    #unique-advice-container {
        width: 100%;
        overflow: hidden;
        white-space: nowrap;
        position: relative;
        font-size: 24px;
        color: blue;
        margin: 10px 0;
    }
    .advice-text {
        display: inline-block;
        animation: scroll 10s linear infinite;
    }
    @keyframes scroll {
        0% {
            transform: translateX(100%);
        }
        100% {
            transform: translateX(-100%);
        }
    }
    </style>
    <div id="unique-advice-container">
        <span id="advice-text" class="advice-text"></span>
    </div>
    <script>
        const advices = [
            "Crée un site web simple pour présenter ton CV interactif.",
                            "Ajoute un QR code à ton CV renvoyant à ton portfolio.",
                            "Personnalise ton CV en utilisant des graphiques ou infographies.",
                            "Contacte des anciens de ton secteur sur LinkedIn pour des conseils.",
                            "Utilise un tableau Kanban (ex. Trello) pour suivre tes candidatures.",
                            "Propose un projet concret ou une idée lors de tes candidatures.",
                            "Prépare un elevator pitch d'une minute en vidéo et partage-le.",
                            "Crée une alerte Google pour suivre les entreprises cibles.",
                            "Utilise des mots-clés précis dans ton profil LinkedIn (ex : Python, SQL).",
                            "Ajoute des recommandations LinkedIn en demandant à tes anciens collègues.",
                            "Participe à des hackathons ou challenges en ligne pour te faire remarquer.",
                            "Fais un audit de tes soft skills et valorise-les dans ta candidature.",
                            "Postule directement par email à des responsables RH avec une approche originale.",
                            "Crée un tableau comparatif des offres pour identifier les meilleures.",
                            "Simule un entretien avec un ami et filme-toi pour t'améliorer.",
                            "Mentionne un détail spécifique de l’entreprise dans ta lettre de motivation.",
                            "Ajoute des certifications en ligne (Coursera, Udemy, OpenClassrooms) à ton profil.",
                            "Personnalise ton portfolio avec des projets liés aux missions de l’offre.",
                            "Utilise les outils d’intelligence artificielle pour optimiser tes candidatures.",
                            "Participe à des salons de l’emploi virtuels pour élargir tes contacts.",
                            "Aborde des recruteurs sur LinkedIn avec une introduction personnalisée.",
                            "Prépare une version anglaise de ton CV pour des opportunités internationales.",
                            "Enregistre un podcast ou une vidéo pour parler de tes compétences.",
                            "Ajoute des projets collaboratifs open-source à ton portfolio.",
                            "Utilise Notion pour organiser tes recherches et entretiens.",
                            "Rédige des articles sur LinkedIn pour montrer ton expertise dans un domaine.",
                            "Rejoins des groupes professionnels sur LinkedIn ou Facebook pour réseauter.",
                            "Crée un visuel accrocheur pour ton profil LinkedIn (ex : bannière personnalisée).",
                            "Souligne ton impact avec des chiffres dans ton CV (ex : KPI atteints).",
                            "Envoie une carte de remerciement après chaque entretien pour marquer l'esprit.",
                            "Postule à des offres cachées en contactant directement les entreprises.",
                            "Optimise ton email de candidature avec une structure claire et efficace.",
                            "Crée une vidéo de présentation créative pour accompagner ton CV.",
                            "Teste différents formats de CV pour voir lequel obtient le plus de retours.",
                            "Apprends à négocier ton salaire avec des simulateurs et des recherches.",
                            "Rejoins des forums comme Reddit ou Slack pour partager des conseils d’emploi.",
                            "Utilise des outils comme Canva pour créer des supports visuels originaux.",
                            "Analyse des descriptions de poste pour ajuster ton vocabulaire.",
                            "Prépare des anecdotes concrètes pour illustrer tes compétences en entretien.",
                            "Relance poliment après une candidature ou un entretien sans réponse"
        ];
        const adviceElement = document.getElementById("advice-text");
        function updateAdvice() {
            const randomAdvice = advices[Math.floor(Math.random() * advices.length)];
            adviceElement.innerText = randomAdvice;
        }
        updateAdvice(); // Affiche immédiatement un premier conseil
        setInterval(updateAdvice, 10000); // Met à jour toutes les 10 secondes
    </script>
    """
    components.html(html_code, height=150)


def main():
    st.title("Finder - Application de recherche d'emploi intelligente")
    if "page" not in st.session_state:
        st.session_state["page"] = "upload"

    if st.session_state["page"] == "upload":
        cv_file = upload_cv()
        if cv_file and (
            "keywords_domaine" not in st.session_state
            or "keywords_intitule" not in st.session_state
            or "cv_analysis" not in st.session_state
        ):
            # CSS pour agrandir le texte du spinner
            st.markdown(
                """
                <style>
                .stSpinner > div > div {
                    font-size: 2rem !important; /* Taille agrandie du spinner */
                }
                </style>
                """,
                unsafe_allow_html=True,
            )
            # Spinner avec texte agrandi
            with st.spinner("Finder est en train d'analyser votre CV pour vous proposer des offres d'emploi qui vous correspondent..."):
                keywords_domaine, keywords_intitule, analysis = get_keywords_from_cv(cv_file)
            if keywords_domaine and keywords_intitule and analysis:
                st.session_state["keywords_domaine"] = keywords_domaine
                st.session_state["keywords_intitule"] = keywords_intitule
                st.session_state["cv_analysis"] = analysis

        if "keywords_domaine" in st.session_state and "keywords_intitule" in st.session_state:
            # Définition des placeholders
            placeholder_domaine = "Sélectionnez un domaine"
            placeholder_intitule = "Sélectionnez un intitulé de métier"
            # Les options avec placeholder en première position
            options_domaine = [placeholder_domaine] + st.session_state["keywords_domaine"]
            options_intitule = [placeholder_intitule] + st.session_state["keywords_intitule"]

            col1, col2 = st.columns(2)
            with col1:
                # On utilise un selectbox pour le domaine
                selected_domaine = st.selectbox(
                    "Sélectionnez un domaine :",
                    options=options_domaine,
                    index=0,
                    key="selected_domaine",
                    on_change=lambda: st.session_state.update({"selected_intitule": placeholder_intitule}),
                )
            with col2:
                # On utilise un selectbox pour l'intitulé
                selected_intitule = st.selectbox(
                    "Sélectionnez un intitulé de métier :",
                    options=options_intitule,
                    index=0,
                    key="selected_intitule",
                    on_change=lambda: st.session_state.update({"selected_domaine": placeholder_domaine}),
                )
            # Affichage de la consigne pour l'utilisateur
            st.info("Veuillez sélectionner soit un domaine, soit un intitulé de métier.")
            
            # Initialisation de la variable `selection`
            selection = None  # Par défaut, aucune sélection

            # Détermination de la sélection unique
            if selected_domaine != placeholder_domaine and selected_intitule != placeholder_intitule:
                st.error("Vous ne pouvez sélectionner qu'un seul mot, soit un domaine, soit un intitulé.")
            elif selected_domaine != placeholder_domaine:
                selection = selected_domaine
            elif selected_intitule != placeholder_intitule:
                selection = selected_intitule

            # Vérification avant utilisation
            if selection is None:
                st.warning("Veuillez effectuer une sélection avant de continuer.")
            else:
                if st.button("Trouver des offres d'emploi"):
                    display_advice()  # Affiche le scrolling des conseils via st.components.v1.html
                    df_offers = get_job_offers(selection)
                    if df_offers is not None:
                        st.session_state["df_offers"] = df_offers
                        st.session_state["page"] = "dashboard"
                        st.rerun()


    elif st.session_state["page"] == "dashboard":
        if "df_offers" in st.session_state:
            display_dashboard(st.session_state["df_offers"])
    elif st.session_state["page"] == "offers":
        if "filtered_df" in st.session_state:
            display_offers(st.session_state["filtered_df"])


if __name__ == "__main__":
    main()

