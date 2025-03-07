import streamlit as st
from streamlit_option_menu import option_menu
from openai import OpenAI
import os
import pandas as pd
import json, requests, time, re
from datetime import datetime, timedelta, timezone
import fitz  # pour lire les PDF
import folium, tempfile
import plotly.express as px
import webbrowser
from dotenv import load_dotenv
from PIL import Image
import streamlit.components.v1 as components
from openai import OpenAI
import numpy as np


client = OpenAI(api_key=st.secrets["openai_key"])

# ===============================
# Configuration Générale
# ===============================
st.set_page_config(page_title="FINDER", layout="wide",page_icon="🎯")

if "job_offer" not in st.session_state:
    st.session_state["job_offer"] = None

if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Initialisation des états de session
if "chatbot_open" not in st.session_state:
    st.session_state.chatbot_open = False  # Chatbot fermé par défaut

if "finder_page" not in st.session_state:
    st.session_state["finder_page"] = "upload"

# ===============================
# Menu Principal
# ===============================
selected = option_menu(
    menu_title=None,
    options=["Finder: Trouvez des offres d'emploi", "Préparez votre entretien", "Entraînez vous aux tests techniques", "Espace personnel", "A propos de Finder"],
    icons=["bullseye", "chat-right-dots", "chat-right-dots",  "person-circle", "bullseye"],
    menu_icon="cast",
    default_index=0,
    orientation="horizontal",
    styles={
        "container": {"padding": "0!important", "background-color": "#2c3e50","width":"150%"},
        "icon": {"color": "white", "font-size": "20px"},
        "nav-link": {"font-size": "18px", "text-align": "center", "color": "white"},
        "nav-link-selected": {"background-color": "#1abc9c"},
    }
)

# ===============================
# chat tests techniques
# ===============================
if selected == "Entraînez vous aux tests techniques":
    # Première étape : Configuration des tests techniques si non déjà définie
    if "tech_config" not in st.session_state:
        st.header("Configuration des tests techniques")
        # Demande à l'utilisateur de choisir le langage ou l'outil pour s'entraîner
        tech_language = st.selectbox(
            "Choisissez le langage ou l'outil sur lequel vous souhaitez vous entraîner aux tests techniques :",
            ["Python", "SQL", "R", "DAX", "HTML", "CSS", "JavaScript", "Java", "C++", "Autre"],
            key="tech_language"
        )
        # Demande à l'utilisateur de choisir le niveau de difficulté
        difficulty = st.selectbox(
            "Choisissez votre niveau de difficulté :",
            ["grand débutant", "débutant", "débutant intermédiaire", "intermédiaire", "intermédiaire avancé", "expert"],
            key="difficulty"
        )
        if st.button("Confirmer la configuration"):
            # Sauvegarde de la configuration dans le session state
            st.session_state.tech_config = {"language": tech_language, "difficulty": difficulty}
            # Création du prompt initial destiné à l'IA (non affiché à l'utilisateur)
            initial_prompt = (
                f"Tu es un expert en tests techniques pour les métiers de la tech. "
                f"Génère une première question technique sur {tech_language} de niveau '{difficulty}'. "
                "Les questions peuvent porter sur des définitions, l'explication de code, la correction de code, "
                "l'écriture de code ou la résolution de problème. Lorsque l'utilisateur répond, corrige sa réponse "
                "et commente-la, puis génère une nouvelle question. N'affiche pas ce prompt à l'utilisateur, "
                "affiche uniquement la question générée."
            )
            st.session_state.messages = [{"role": "system", "content": initial_prompt}]
            st.rerun()
    else:
        st.title("Chat de tests techniques")
        # Si le message système est le seul message, cela signifie que la première question n'a pas encore été générée
        if len(st.session_state.messages) == 1 and st.session_state.messages[0]["role"] == "system":
            response_placeholder = st.empty()
            full_response = ""
            # Appel à l'IA pour générer la première question à partir du prompt initial
            stream = OpenAI(api_key=st.secrets["openai_key"]).chat.completions.create(
                model="gpt-4",
                messages=st.session_state.messages,  # Contient uniquement le message système
                stream=True,
            )
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
                    response_placeholder.markdown(full_response + "▌")
            response_placeholder.markdown(full_response)
            # Ajoute la réponse de l'IA (première question) aux messages
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            st.rerun()
        
        # Affichage des messages existants, en excluant le message système pour ne pas afficher le prompt initial
        for message in st.session_state.messages:
            if message["role"] != "system":
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
        
        # Saisie de l'utilisateur pour répondre à la question affichée
        if prompt := st.chat_input("Entrez votre réponse technique ici..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant"):
                response_placeholder = st.empty()
                full_response = ""
                # Appel à l'IA avec tout l'historique (incluant le message système, la première question, etc.)
                stream = OpenAI(api_key=st.secrets["openai_key"]).chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages],
                    stream=True,
                )
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        full_response += chunk.choices[0].delta.content
                        response_placeholder.markdown(full_response + "▌")
                response_placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})




# ===============================
# Pages du Menu Principal
# ===============================
if selected == "Accueil":
    st.title("FINDER")
    st.title("Votre assistant personnel de recherche d'emploi.")

elif selected == "A propos de Finder":
    st.title("A propos de Finder")
    st.markdown("""
Finder est une application web innovante conçue pour faciliter la recherche d'emploi en automatisant l'analyse de CV et la mise en relation avec des offres pertinentes. Grâce à l'intégration d'outils d'intelligence artificielle et d'API spécialisées, Finder simplifie et optimise le parcours des candidats en leur fournissant des recommandations personnalisées et des outils de suivi efficaces.

**Fonctionnalités principales**

**Analyse intelligente du CV**  
- Extraction automatique des compétences techniques (hard skills) et comportementales (soft skills).  
- Identification des domaines d'expertise et des intitulés de postes correspondants.  
- Traitement basé sur l'IA pour une analyse précise et pertinente.

**Recherche d'offres d'emploi ciblée**  
- Connexion à l'API France Travail pour récupérer les offres en temps réel.  
- Recherche basée sur un mot-clé unique (domaine ou intitulé de poste).  
- Interface interactive avec des filtres dynamiques pour affiner les résultats.

**Génération de lettres de motivation personnalisées**  
- Rédaction automatique d'une lettre adaptée à l’offre sélectionnée et aux compétences du candidat.  
- Format téléchargeable et prêt à être modifié selon les besoins.

**Tableau de suivi des candidatures**  
- Sauvegarde des offres retenues avec les détails clés (date de candidature, numéro d’offre, lien de l’offre, lieu de travail).  
- Programmation automatique des dates de relance pour un suivi optimisé.

**Conseils dynamiques pour la recherche d’emploi**  
- Affichage de recommandations stratégiques pendant l’utilisation de l’application.  
- Mise à jour automatique pour s’adapter au contexte du candidat.

**Pourquoi utiliser Finder ?**  
- Gain de temps : Analyse rapide du CV et accès direct aux offres pertinentes.  
- Personnalisation : Résultats adaptés aux compétences et au profil du candidat.  
- Efficacité : Suivi structuré des candidatures avec rappels intégrés.  
- Sécurité : Protection des données personnelles et respect de la confidentialité.  
- Accessibilité : Interface intuitive et conviviale pour tous les utilisateurs.
    """)

    
elif selected == "Préparez votre entretien":
    st.subheader("Pour une meilleure personnalisation de votre simulation d'entretien, uploadez votre CV sur la page d'accueil si vous ne l'avez pas fait.")

    

    # ----------------------
    # LISTE DE QUESTIONS STANDARDS
    # ----------------------
    standard_questions = [
        "Pouvez-vous vous présenter ?",
        "Que savez-vous de nous ?",
        "Qu’est-ce qui a suscité votre intérêt dans cette offre d’emploi ?",
        "Pourquoi souhaitez-vous travailler avec nous ?",
        "Pourquoi souhaitez-vous quitter votre poste actuel ?",
        "Que pouvez-vous dire sur votre ancien employeur ?",
        "Où avez-vous postulé ?",
        "Pourquoi êtes-vous le candidat idéal ?",
        "Comment expliquez-vous ce trou dans votre parcours ?",
        "Parlez-moi d’une situation où vous avez réussi à dénouer un problème complexe...",
        "Racontez-moi un projet professionnel dont vous êtes particulièrement fier...",
        "Quels résultats avez-vous obtenu dans vos précédentes expériences ?",
        "Comment organisez-vous votre prospection commerciale ?",
        "De quelle négociation êtes-vous le plus fier ?",
        "Quelle est la critique la plus constructive qu’on a été amené à vous faire ?",
        "Comment gérez-vous la critique ?",
        "Etes-vous un leader ?",
        "Etes-vous capable de travailler sous pression ?",
        "Si vous pouviez revenir dans le passé, feriez-vous différemment certaines choses ?",
        "Qu’aimeriez-vous faire une fois en poste ?",
        "Comment comptez-vous entrer en interaction avec votre nouvel environnement de travail ?",
        "Qu'est-ce qui selon vous va vous poser des difficultés dans ce poste ?",
        "Qu’attendez-vous de votre manager ?",
        "Quelles sont vos attentes concernant l’organisation de travail ?",
        "Quels sont vos axes d’amélioration ?",
        "Quel regard portent sur vous vos collègues et amis ?",
        "Êtes-vous prêt à échouer ?",
        "Quels sont vos moteurs professionnels ?",
        "Avec quelle philosophie abordez-vous votre travail ?",
        "Où vous voyez-vous dans cinq ans ?",
        "Comment souhaitez-vous construire votre carrière ?",
        "Quel est votre projet professionnel ?",
        "Quel est le poste idéal pour vous ?",
        "Avez-vous développé des compétences extraprofessionnelles que vous souhaiteriez valoriser ?",
        "Quel regard portez-vous sur votre métier, votre secteur d’activité, ses enjeux actuels ?",
        "Quelles sont vos prétentions salariales ?",
        "Quelle est votre disponibilité ?",
        "Quels sont vos hobbies ?",
        "Avez-vous des questions ?"
    ]

    # Récupération de l'analyse de CV (si disponible)
    cv_analysis = st.session_state.get("cv_analysis", "Aucune analyse de CV disponible")

    # Variable pour stocker l'offre d'emploi
    if "job_offer" not in st.session_state:
            st.session_state.job_offer = None

    # Stockage des messages
    if "messages" not in st.session_state:
            st.session_state.messages = []

    # Index de question, pour limiter à N questions
    if "current_question_index" not in st.session_state:
            st.session_state.current_question_index = 0

    # ----------------------
    # FONCTION : Générer une question personnalisée
    # ----------------------
    def generate_personalized_question(cv_analysis_text, job_offer_text):
        """
        Pose une question unique et personnalisée, 
        basée sur le contenu du CV et sur l'offre d'emploi.
        """
        prompt_personnalise = f"""
Tu es un coach spécialisé en entretien d'embauche.
Tu vas poser une question unique, adaptée au profil du candidat (analyse du CV ci-dessous) et à l'offre d'emploi suivante.
- Analyse du CV : {cv_analysis_text}
- Offre d'emploi : {job_offer_text}

Rédige une question pertinente pour un entretien d'embauche, 
en lien avec l'offre et le CV. 
Donne uniquement la question, sans préambule ni commentaire supplémentaire.
        """
        # On utilise la même clé / modèle que dans get_keywords_from_cv
        model = "gpt-4o-mini"
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt_personnalise}],
            max_tokens=300,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()

    # ----------------------
    # FONCTION : Sélectionner la prochaine question (standard OU personnalisée)
    # ----------------------
    import random
    def get_next_question(cv_analysis_text, job_offer_text):
        """
        Selon un pourcentage aléatoire, renvoie :
        - soit une question standard,
        - soit une question personnalisée (CV + offre).
        """
        # On fait par exemple un tirage 50 / 50
        if random.random() < 0.5:
            # On prend une question standard au hasard
            return random.choice(standard_questions)
        else:
            # On prend une question personnalisée
            return generate_personalized_question(cv_analysis_text, job_offer_text)

    # ----------------------
    # FONCTION : Évaluer la réponse du candidat
    # ----------------------
    def evaluate_response(question, response):
        """
        Evalue la réponse du candidat : 
        - Feedback constructif
        - Réponse modèle
        - Conseil
        On utilise le même modèle que get_keywords_from_cv
        """
        prompt_text = f"""
Tu es un coach en entretien d'embauche. 
Analyse et commente la réponse du candidat pour la question suivante :
Question : {question}
Réponse du candidat : {response}

Demandes :
1. Fais une analyse critique de la réponse. 
2. Donne un feedback constructif.
3. Fournis une réponse modèle pour s'améliorer.
4. Termine par un conseil pour mieux répondre à cette question à l'avenir = SI NECESSAIRE.

Format attendu :

Feedback : [Ton feedback]
Réponse modèle : [Réponse modèle]
Conseil : [Conseil]
        """
        model = "gpt-4o-mini"  # Même modèle qu'au-dessus
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": prompt_text},
                {"role": "user", "content": response}
            ],
            max_tokens=3000,
            temperature=0.5
        )
        return resp.choices[0].message.content.strip()

    # ==================================================
    # 1) DEMANDE INITIALE : Inviter l'utilisateur à coller l'offre d'emploi
    # ==================================================
    if st.session_state.job_offer is None:
        # Si on n'a pas encore stocké l'offre, on demande de la coller
        if len(st.session_state.messages) == 0 or st.session_state.messages[-1]["role"] == "assistant":
            msg_offre = "Veuillez coller ici l'offre d'emploi pour laquelle vous souhaitez préparez un entretien d'embauche."
            st.session_state.messages.append({"role": "assistant", "content": msg_offre})
            with st.chat_message("assistant"):
                st.markdown(msg_offre)

        # Lecture de la réponse de l'utilisateur (offre d'emploi)
        if prompt := st.chat_input("Votre réponse..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # On sauvegarde l'offre d'emploi
            st.session_state.job_offer = prompt

            # Génération de la première question (standard ou perso)
            first_question = get_next_question(cv_analysis, st.session_state.job_offer)
            st.session_state.messages.append({"role": "assistant", "content": f"**Question :** {first_question}"})
            with st.chat_message("assistant"):
                st.markdown(f"**Question :** {first_question}")

    else:
        # ==================================================
        # 2) LOGIQUE DE QUESTIONS / REPONSES
        # ==================================================
        if prompt := st.chat_input("Votre réponse..."):
            # L'utilisateur vient de répondre
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # Récupère la dernière question posée par l'assistant
            last_question = None
            for msg in reversed(st.session_state.messages):
                if msg["role"] == "assistant" and msg["content"].strip().startswith("**Question :**"):
                    last_question = msg["content"].replace("**Question :**", "").strip()
                    break

            # Evalue la réponse du candidat (feedback + conseils)
            if last_question:
                feedback_text = evaluate_response(last_question, prompt)
                st.session_state.messages.append({"role": "assistant", "content": f"**Feedback :**\n{feedback_text}"})
                with st.chat_message("assistant"):
                    st.markdown(f"**Feedback :**\n{feedback_text}")

            # Incrémente l'index pour savoir où on en est
            st.session_state.current_question_index += 1

            # Choisit un nombre limite de questions, ici 10
            if st.session_state.current_question_index >= 10:
                fin_msg = "🎉 Félicitations ! Vous avez terminé ces questions. Vous êtes maintenant prêt pour votre entretien !"
                st.session_state.messages.append({"role": "assistant", "content": fin_msg})
                with st.chat_message("assistant"):
                    st.markdown(fin_msg)
            else:
                # Pose la question suivante (standard ou perso)
                next_q = get_next_question(cv_analysis, st.session_state.job_offer)
                msg_suiv = f"**Question suivante :** {next_q}\n\n*Conseil : Restez concis et pertinent.*"
                st.session_state.messages.append({"role": "assistant", "content": msg_suiv})
                with st.chat_message("assistant"):
                    st.markdown(msg_suiv)



elif selected == "Finder: Trouvez des offres d'emploi":
    st.title("Finder - Application de recherche d'emploi intelligente")
    st.subheader("Faisons connaissance: Glissez votre CV ci-dessous et laissez vous guider.")

    # Initialisation des clés spécifiques pour Finder
    load_dotenv()
    api_key_ft = st.secrets["API_KEY_FT"]
    client_id_ft = st.secrets["CLIENT_ID_FT"]

    # -------------------------------
    # Fonctions pour l'application Finder
    # -------------------------------
    def upload_cv():
        return st.file_uploader("Uploadez votre CV en PDF", type=["pdf"], key="cv_uploader")

    def extract_text_from_pdf(pdf_file):
        try:
            pdf_file.seek(0)
            pdf_bytes = pdf_file.read()
            if not pdf_bytes:
                st.error("Le fichier PDF semble être vide.")
                return None
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            text = ""
            for page in doc:
                text += page.get_text("text") + "\n"
            return text.strip()
        except Exception as e:
            st.error(f"Erreur lors de la lecture du PDF : {e}")
            return None

    def get_keywords_from_cv(cv_file):
        if cv_file is None:
            st.error("Aucun fichier CV détecté.")
            return None, None, None
        cv_text = extract_text_from_pdf(cv_file)
        if not cv_text:
            st.error("Impossible d'extraire le texte du CV.")
            return None, None, None
        keywords_domaine_prompt = "Donne uniquement ces deux mots exacts et dans cet ordre, séparés par une virgule : Data, Développeur"
        keywords_intitule_prompt = f"""Identifie entre 3 et 8 intitulés de métiers qui correspondent au texte ci-dessous.
Donne uniquement les intitulés séparés par des virgules, sans explication, sans texte supplémentaire.
Texte : {cv_text}"""
        analysis_prompt = f"""Retourne uniquement un objet JSON contenant les éléments suivants, ne retourne que ce qui est explicitement écrit dans le cv :
{{
  "soft_skills": ["liste des soft skills"],
  "hard_skills": ["liste des hard skills"],
  "savoir_faire": ["liste des savoir-faire"],
  "savoir_etre": ["liste des savoir-être"]
}}
Ne donne aucune explication supplémentaire.
Texte : {cv_text}"""
        try:
            model = "gpt-4o-mini"
            keywords_domaine_response = client.chat.completions.create(model=model,
            messages=[{"role": "user", "content": keywords_domaine_prompt}])
            keywords_intitule_response = client.chat.completions.create(model=model,
            messages=[{"role": "user", "content": keywords_intitule_prompt}])
            analysis_response = client.chat.completions.create(model=model,
            messages=[{"role": "user", "content": analysis_prompt}])
            keywords_domaine_raw = keywords_domaine_response.choices[0].message.content.strip()
            keywords_domaine = [kw.strip() for kw in keywords_domaine_raw.split(",") if kw.strip()]
            keywords_intitule_raw = keywords_intitule_response.choices[0].message.content.strip()
            keywords_intitule = [kw.strip() for kw in keywords_intitule_raw.split(",") if kw.strip()]
            analysis_raw = analysis_response.choices[0].message.content.strip()
            if not analysis_raw:
                st.error("La réponse de l'IA est vide.")
                return None, None, None
            analysis_clean = re.sub(r"^```(?:json)?\s*", "", analysis_raw)
            analysis_clean = re.sub(r"\s*```$", "", analysis_clean)
            analysis_clean = re.sub(r"<[^>]*>", "", analysis_clean)
            try:
                analysis = json.loads(analysis_clean)
            except json.JSONDecodeError as e:
                st.error(f"Erreur de décodage JSON : {str(e)}. Réponse nettoyée : {analysis_clean}")
                return None, None, None
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
        if not mot_cle:
            st.error("Aucun mot-clé fourni pour la recherche d'emploi.")
            return None
        st.write(f"Recherche d'offres pour le mot clé: {mot_cle}")
        start_time = time.time()
        client_id = client_id_ft
        client_secret = api_key_ft
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
        step = 50
        max_results = 3000
        ft_progress = st.progress(0)
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
                ft_progress.progress(min(100, int((start / max_results) * 100)))
            else:
                st.error(f"Erreur lors de la requête : {response.status_code}")
                break
        ft_progress.empty()
        print(f"{len(all_offers)} offres récupérées.")
        if all_offers:
            df = pd.json_normalize(all_offers)
            df.columns = df.columns.str.replace(".", "_")
            if "dateCreation" in df.columns:
                df["dateCreation"] = pd.to_datetime(df["dateCreation"], utc=True).dt.tz_convert(None)
                date_limit = datetime.now(timezone.utc) - timedelta(days=10)
                date_limit = date_limit.replace(tzinfo=None)
                df_recent = df[df["dateCreation"] >= date_limit]
                print(f"Données enregistrées : {len(df)} offres totales, {len(df_recent)} des 10 derniers jours.")
                elapsed_time = time.time() - start_time
                print(f"Temps d'exécution total : {elapsed_time:.2f} secondes")
                return df_recent
        return None

    def departement(text):
        text = str(text).strip()
        if text.lower() == "france":
            return "France entière"
        match = re.match(r"^(2A|2B|\d{1,3})", text)
        if match:
            numero = match.group()
        else:
            return text
        departements = {
            "01": "Ain", "02": "Aisne", "03": "Allier", "04": "Alpes-de-Haute-Provence",
            "05": "Hautes-Alpes", "06": "Alpes-Maritimes", "07": "Ardèche", "08": "Ardennes",
            "09": "Ariège", "10": "Aube", "11": "Aude", "12": "Aveyron", "13": "Bouches-du-Rhône",
            "14": "Calvados", "15": "Cantal", "16": "Charente", "17": "Charente-Maritime",
            "18": "Cher", "19": "Corrèze", "2A": "Corse-du-Sud", "2B": "Haute-Corse",
            "21": "Côte-d'Or", "22": "Côtes-d'Armor", "23": "Creuse", "24": "Dordogne",
            "25": "Doubs", "26": "Drôme", "27": "Eure", "28": "Eure-et-Loir", "29": "Finistère",
            "30": "Gard", "31": "Haute-Garonne", "32": "Gers", "33": "Gironde", "34": "Hérault",
            "35": "Ille-et-Vilaine", "36": "Indre", "37": "Indre-et-Loire", "38": "Isère",
            "39": "Jura", "40": "Landes", "41": "Loir-et-Cher", "42": "Loire", "43": "Haute-Loire",
            "44": "Loire-Atlantique", "45": "Loiret", "46": "Lot", "47": "Lot-et-Garonne",
            "48": "Lozère", "49": "Maine-et-Loire", "50": "Manche", "51": "Marne",
            "52": "Haute-Marne", "53": "Mayenne", "54": "Meurthe-et-Moselle", "55": "Meuse",
            "56": "Morbihan", "57": "Moselle", "58": "Nièvre", "59": "Nord", "60": "Oise",
            "61": "Orne", "62": "Pas-de-Calais", "63": "Puy-de-Dôme", "64": "Pyrénées-Atlantiques",
            "65": "Hautes-Pyrénées", "66": "Pyrénées-Orientales", "67": "Bas-Rhin", "68": "Haut-Rhin",
            "69": "Rhône", "70": "Haute-Saône", "71": "Saône-et-Loire", "72": "Sarthe",
            "73": "Savoie", "74": "Haute-Savoie", "75": "Paris", "76": "Seine-Maritime",
            "77": "Seine-et-Marne", "78": "Yvelines", "79": "Deux-Sèvres", "80": "Somme",
            "81": "Tarn", "82": "Tarn-et-Garonne", "83": "Var", "84": "Vaucluse", "85": "Vendée",
            "86": "Vienne", "87": "Haute-Vienne", "88": "Vosges", "89": "Yonne",
            "90": "Territoire de Belfort", "91": "Essonne", "92": "Hauts-de-Seine",
            "93": "Seine-Saint-Denis", "94": "Val-de-Marne", "95": "Val-d'Oise",
            "971": "Guadeloupe", "972": "Martinique", "973": "Guyane", "974": "La Réunion",
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
                    "competences", "dureeTravailLibelle", "dureeTravailLibelleConverti", "deplacementCode",
                    "deplacementLibelle", "qualificationCode", "qualificationLibelle", "codeNAF",
                    "secteurActivite", "secteurActiviteLibelle", "offresManqueCandidats", "entreprise_nom",
                    "salaire_libelle", "salaire_complement1", "salaire_complement2", "contact_nom",
                    "contact_coordonnees1", "contact_courriel", "contexteTravail_conditionsExercice", "formations",
                    "entreprise_logo", "contact_urlPostulation", "langues", "qualitesProfessionnelles",
                    "salaire_commentaire", "entreprise_url", "permis", "experienceCommentaire",
                    "contact_coordonnees2", "contact_coordonnees3", "agence_courriel", "complementExercice",
                    "nombrePostes", "origineOffre_partenaires", "lieuTravail_commune", "dateActualisation",
                    "origineOffre_origine", "entreprise_entrepriseAdaptee", "natureContrat",
                ],
                axis=1,
                errors="ignore",
            )
            print("Données nettoyées avec succès.")
            rome_counts = df_clean["romeLibelle"].value_counts(normalize=True) * 100
            rome_above_3 = rome_counts[np.round(rome_counts, 2) > 3].index
            df_final = df_clean[df_clean["romeLibelle"].isin(rome_above_3)].copy()
            df_final["departement"] = df_final["lieuTravail_libelle"].apply(departement)
            return df_final
        else:
            print("Aucune offre récente récupérée, nettoyage impossible.")
            return None

    def remplacer_type_contrat(type_contrat):
        mapping = {
            "CDI": "CDI",
            "CDD": "CDD",
            "SAI": "SAISONNIER",
            "MIS": "MISSION",
            "FRA": "FRANCHISE",
        }
        return mapping.get(type_contrat, "AUTRES")

    def filter_offers(df_final, selected_departement=None, selected_typeContrat=None, selected_intitule=None, selected_keywords=None):
        filtered_df = df_final.copy()
        if selected_departement:
            if isinstance(selected_departement, str):
                selected_departement = [selected_departement]
            filtered_df = filtered_df[filtered_df["departement"].isin(selected_departement)]
        if selected_typeContrat:
            if isinstance(selected_typeContrat, str):
                selected_typeContrat = [selected_typeContrat]
            filtered_df = filtered_df[filtered_df["typeContrat"].isin(selected_typeContrat)]
        if selected_intitule:
            if isinstance(selected_intitule, str):
                selected_intitule = [selected_intitule]
            regex_pattern = '|'.join(selected_intitule)
            filtered_df = filtered_df[filtered_df["appellationlibelle"].str.contains(regex_pattern, case=False, na=False)]
        if selected_keywords:
            if isinstance(selected_keywords, str):
                selected_keywords = [selected_keywords]
            filtered_df = filtered_df[filtered_df['appellationlibelle'].str.contains('|'.join(selected_keywords), case=False, na=False)]
        return filtered_df

    def display_map(filtered_options):
        if filtered_options is not None and not filtered_options.empty:
            m = folium.Map(location=[48.8566, 2.3522], zoom_start=6)
            for _, row in filtered_options.iterrows():
                if pd.notna(row['lieuTravail_latitude']) and pd.notna(row['lieuTravail_longitude']):
                    folium.Marker(
                        location=[row['lieuTravail_latitude'], row['lieuTravail_longitude']],
                        popup=f"Poste: {row['appellationlibelle']}<br>Département: {row['departement']}",
                        icon=folium.Icon(color='orange', icon='phone')
                    ).add_to(m)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as f:
                m.save(f.name)
                st.components.v1.html(open(f.name, 'r').read(), height=550)
        else:
            st.write("⚠️ Aucune donnée géographique disponible.")

    def display_dashboard(df_offers):
        st.subheader("TABLEAU DE BORD")
        base_df = df_offers.copy()
        base_df['typeContrat'] = base_df['typeContrat'].apply(remplacer_type_contrat)
        all_departements = sorted(base_df["departement"].unique())
        for key in ["selected_departement", "selected_typeContrat", "selected_intitule"]:
            if key not in st.session_state:
                st.session_state[key] = []
            if not isinstance(st.session_state[key], list):
                st.session_state[key] = []
        col1, col2, col3 = st.columns([1, 2, 2])
        with col1:
            valid_dept_defaults = [d for d in st.session_state.selected_departement if d in all_departements]
            selected_departement = st.multiselect(
                "Département",
                options=all_departements,
                default=valid_dept_defaults,
                key="departement_select"
            )
            st.session_state.selected_departement = selected_departement
        dept_filtered_df = base_df
        if selected_departement:
            dept_filtered_df = base_df[base_df["departement"].isin(selected_departement)]
        available_contracts = sorted(dept_filtered_df["typeContrat"].unique())
        with col2:
            valid_contracts = [c for c in st.session_state.selected_typeContrat if c in available_contracts]
            selected_typeContrat = st.multiselect(
                "Type de contrat",
                options=available_contracts,
                default=valid_contracts,
                key="typeContrat_select"
            )
            st.session_state.selected_typeContrat = selected_typeContrat
        contract_filtered_df = dept_filtered_df
        if selected_typeContrat:
            contract_filtered_df = dept_filtered_df[dept_filtered_df["typeContrat"].isin(selected_typeContrat)]
        available_intitules = sorted(contract_filtered_df["appellationlibelle"].unique())
        with col3:
            valid_intitules = [i for i in st.session_state.selected_intitule if i in available_intitules]
            selected_intitule = st.multiselect(
                "Intitulé du poste",
                options=available_intitules,
                default=valid_intitules,
                key="intitule_select"
            )
            st.session_state.selected_intitule = selected_intitule
        filtered_options = contract_filtered_df
        if selected_intitule:
            filtered_options = contract_filtered_df[contract_filtered_df["appellationlibelle"].isin(selected_intitule)]
        if filtered_options.empty:
            st.warning("Aucune donnée ne correspond aux critères de filtrage.")
        # else:
        #     st.success(f"{len(filtered_options)} résultats trouvés.")
        if selected_intitule:
            mot_cle = selected_intitule[0]
        elif selected_departement:
            mot_cle = selected_departement[0]
        elif st.session_state.get("selected_keywords"):
            mot_cle = st.session_state.selected_keywords[0]
        # else:
        #     mot_cle = None
        # if mot_cle:
        #     st.write(f"Mot clé utilisé pour la recherche: {mot_cle}")
        else:
            st.write("Aucun mot-clé sélectionné pour la recherche.")
        if st.button("Voir les offres"):
            st.session_state["filtered_df"] = filtered_options
            st.session_state["finder_page"] = "offers"
            st.rerun()
        col1, col2, col3 = st.columns([3, 3, 3])
        with col1:
            total_offers = len(filtered_options)
            st.markdown(
                f"""<div style="background-color: transparent; padding: 10px; border-radius: 10px; text-align: center; border: 2px solid black; display: flex; flex-direction: column; justify-content: center; align-items: center; height: 550px;">
                        <p style="color: black; font-size: 100px; font-weight: bold; margin: 0;">{total_offers}</p>
                        <h3 style="color: black; font-family: 'Source Sans Pro', sans-serif; margin: 0;">Annonces</h3>
                    </div>""",
                unsafe_allow_html=True
            )
        with col2:
            st.write("      ")
            if not filtered_options.empty:
                keyword_counts = filtered_options["typeContrat"].value_counts()
                fig_pie = px.pie(
                    values=keyword_counts.values,
                    names=keyword_counts.index,
                    hole=0.2,
                )
                fig_pie.update_traces(
                    textinfo='label+value',
                    textfont=dict(size=20, family="Source Sans Pro", color="black", weight="bold"),
                    pull=[0.1] * len(keyword_counts)
                )
                fig_pie.update_layout(showlegend=False)
                st.plotly_chart(fig_pie, use_container_width=True, height=550)
            st.write("")
        with col3:
            display_map(filtered_options)

    csv_file = "applied_offers.csv"

        # Chargement du fichier CSV uniquement si nécessaire
    if "applied_offers" not in st.session_state:
            if os.path.exists(csv_file):
                df_applied = pd.read_csv(csv_file)
                st.session_state["applied_offers"] = df_applied.to_dict(orient="records")
            else:
                st.session_state["applied_offers"] = []

    if "applied_jobs" not in st.session_state:
        st.session_state["applied_jobs"] = {offer["id"] for offer in st.session_state["applied_offers"]}

    def display_offers(filtered_df):
        st.subheader("Offres d'emploi correspondantes")

        if st.button("Retour au tableau de bord"):
            st.session_state["finder_page"] = "dashboard"
            st.rerun()

        for _, row in filtered_df.iterrows():
            offer_key = row["id"]
            is_applied = offer_key in st.session_state["applied_jobs"]
            text_color = "#007BFF" if is_applied else "#000"
            container_background = "#d1ecf1" if is_applied else "#fff"

            with st.container():
                st.markdown(
                    f"""<div style="background-color: {container_background}; padding: 10px; border-radius: 5px;">
                            <strong style="color: {text_color};">
                                N°{row['id']} - {row['intitule']} | {row['typeContrat']} | {row['lieuTravail_libelle']}
                            </strong>
                        </div>""",
                    unsafe_allow_html=True,
                )
                with st.expander("Voir les détails"):
                    st.write(f"**Description :** {row['description']}")
                    if st.button("Générer une lettre de motivation", key=f"lm_{offer_key}"):
                        cv_analysis = st.session_state.get("cv_analysis")
                        if not cv_analysis:
                            st.error("L'analyse du CV n'a pas été réalisée.")
                        else:
                            generate_cover_letter(cv_analysis, row["description"], row["id"], row["intitule"])

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Voir le lien", key=f"lien_{offer_key}"):
                            url = row.get("origineOffre_urlOrigine", "")
                            if url:
                                webbrowser.open_new_tab(url)
                    with col2:
                        if is_applied:
                            st.markdown(
                                "<button style='background-color: green; color: white; border: none; padding: 6px 12px; border-radius: 4px;'>Postulé</button>",
                                unsafe_allow_html=True
                            )
                        else:
                            if st.button("Postuler", key=f"postuler_{offer_key}"):
                                row_dict = row.to_dict()
                                row_dict["date_candidature"] = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

                                # Vérifier si l'offre n'a pas déjà été ajoutée
                                already_applied = any(offer["id"] == offer_key for offer in st.session_state["applied_offers"])
                                if not already_applied:
                                    st.session_state["applied_jobs"].add(offer_key)
                                    st.session_state["applied_offers"].append(row_dict)

                                    # Sauvegarde cumulative dans le CSV
                                    df_applied = pd.DataFrame(st.session_state["applied_offers"])
                                    df_applied.to_csv(csv_file, index=False)

                                st.success("Vous avez postulé à cette offre !")
                                st.rerun()

        # Section pour télécharger et visualiser les candidatures
        st.subheader("Vos candidatures")
        if st.session_state["applied_offers"]:
            df_applied = pd.DataFrame(st.session_state["applied_offers"])
            
            csv_data = df_applied.to_csv(index=False).encode("utf-8")
            st.download_button("Télécharger vos candidatures",
                data=csv_data,
                file_name="applied_offers.csv",
                mime="text/csv",
                key="download_button_applied_offers"
            )

            # Supprime la colonne 'description' pour un affichage plus clair
            df_applied_no_description = df_applied.drop(columns=["description"], errors="ignore")
            st.table(df_applied_no_description)
        else:
            st.info("Vous n'avez pas encore postulé à une offre.")
            # Section pour télécharger et visualiser les candidatures
            st.subheader("Vos candidatures")
            if st.session_state["applied_offers"]:
                df_applied = pd.DataFrame(st.session_state["applied_offers"])
                
                # Génération du CSV complet (avec la colonne 'description' et 'date_candidature')
                csv_data = df_applied.to_csv(index=False).encode("utf-8")
                st.download_button("Télécharger vos candidatures",
                    data=csv_data,
                    file_name="applied_offers.csv",
                    mime="text/csv",
                    key="download_button_applied_offers"
                )
                
                # Pour l'affichage, on retire la colonne 'description'
                df_applied_no_description = df_applied.drop(columns=["description"], errors="ignore")
                st.table(df_applied_no_description)
            else:
                st.info("Vous n'avez pas encore postulé à une offre.")
        
    def generate_cover_letter(analysis, job_offer_details, offer_id, offer_intitule):
        prompt = f"""**NOUVEAU PROMPT :**

> **Rôle :**  
> Tu es un expert en rédaction de lettres de motivation sur mesure, spécialisées pour des profils professionnels.
>
> **Ta mission :**  
> Rédiger une lettre de motivation convaincante, personnalisée et conforme aux exigences suivantes :
>
> 1. **Respect absolu des informations du CV et de l’offre d’emploi**  
>    - Utilise uniquement les expériences, compétences et projets explicitement mentionnés dans l’_Analyse du CV_ (ci-dessous nommée `{analysis}`).  
>    - Il est strictement interdit de créer, d’imaginer ou de déformer des expériences, diplômes ou compétences pour mieux coller à l’offre.  
>    - Toute formation ou tout diplôme doit être restitué exactement comme indiqué dans le CV.  
>    - **N'insère aucune année d'expérience ou compétence si elle n'est pas mentionnée dans l'Analyse du CV.**  
>    - Si le CV ne précise pas un nombre d'années d'expérience ou un niveau précis, n'en invente pas.
>
> 2. **Structure de la lettre**  
>    - La lettre doit comporter plusieurs paragraphes clairs et cohérents.  
>    - Les paragraphes recommandés sont :  
>       1. **Introduction** : accroche engageante et mention directe du poste.  
>       2. **Profil du candidat** : présentation des expériences réelles (celles présentes dans `{analysis}`), compétences et projets en lien avec le poste.  
>       3. **Apport pour l’entreprise** : mise en avant des correspondances réelles entre {analysis} et`{job_offer_details}`.  
>       4. **Conclusion** : proposition d’entretien, remerciements et expression de la motivation.  
>
> 3. **Tonalité et style**  
>    - Emploie un ton professionnel.  
>    - **Il est formellement interdit** d’utiliser les mots « passion », « enthousiasme » ou leurs déclinaisons.  
>    - Utilise des formulations précises et pertinentes.  
>    - Ne dépasse pas une page de longueur.  
>
> 4. **Exploitation des documents**  
>    - _Analyse du CV_ : `{analysis}`  
>    - _Détails de l’offre d’emploi_ : `{job_offer_details}`  
>    - Tous les éléments utilisés dans ta rédaction doivent provenir exclusivement de ces deux sources.  
>
> 5. **Format attendu**  
>    - La sortie doit être la **lettre de motivation complète**, prête à être utilisée.  
>    - Le texte commencera par une phrase engageante et se terminera par une formule de politesse professionnelle.
>
> **Important** : N’extrapole en aucun cas ; chaque information doit être strictement conforme à `{analysis}`.
"""
        try:
            model = "gpt-4o-mini"
            response = client.chat.completions.create(model=model,
            messages=[{"role": "user", "content": prompt}])
            cover_letter = response.choices[0].message.content.strip()
            file_name = f"{offer_id}_lettre_de_motivation.txt"
            st.download_button(
                label="Télécharger la lettre de motivation",
                data=cover_letter,
                file_name=file_name,
                mime="text/plain",
            )
            return cover_letter
        except Exception as e:
            st.error(f"Erreur lors de la génération de la lettre de motivation : {str(e)}")
            return None

    def display_advice():
        html_code = """
        <style>
        #unique-advice-container {
            width: 100%;
            overflow: hidden;
            white-space: nowrap;
            position: relative;
            font-size: 150%;
            color: #2c2b56;
            margin: 10px 0;
            font-family: "Source Sans Pro", sans-serif;
        }
        .advice-text {
            display: inline-block;
            animation: scroll 10s linear infinite;
        }
        @keyframes scroll {
            0% { transform: translateX(100%); }
            100% { transform: translateX(-100%); }
        }
        </style>
        <div id="unique-advice-container">
            <span id="advice-text" class="advice-text"></span>
        </div>
        <script>
            const advices = [
                "Crée un mini-site ou portfolio GitHub détaillant clairement tes projets en JavaScript, Python ou autres langages clés.",
                "Intègre un QR code pointant directement vers une démo en ligne (ex. app React) pour illustrer concrètement tes compétences.",
                "Participe à un hackathon tech pour prouver tes capacités à résoudre rapidement des défis de programmation en équipe.",
                "Rédige un elevator pitch d’une minute axé sur tes compétences techniques (ex. DevOps, Data Science) et publie-le en vidéo.",
                "Optimise tes mots-clés LinkedIn (ex. Docker, Kubernetes) pour attirer les recruteurs spécialisés en ingénierie logicielle.",
                "Ajoute des contributions open-source (ex. pull requests sur GitHub) pour démontrer ton implication dans la communauté tech.",
                "Configure des alertes Google sur les start-ups ou scale-ups que tu cibles pour personnaliser chaque candidature.",
                "Teste différents formats de CV (version data-driven, format stylisé) et mesure le taux de réponse pour ajuster ta stratégie.",
                "Enregistre-toi en train de résoudre un algorithme en live-coding pour t’entraîner aux entretiens techniques.",
                "Fais relire ton CV et ton GitHub par un pair pour un feedback précis et constructif."
            ];
            const adviceElement = document.getElementById("advice-text");
            function updateAdvice() {
                const randomAdvice = advices[Math.floor(Math.random() * advices.length)];
                adviceElement.innerText = randomAdvice;
            }
            updateAdvice();
            setInterval(updateAdvice, 10000);
        </script>
        """
        components.html(html_code, height=150)

    # -------------------------------
    # Routage interne de Finder
    # -------------------------------
    if st.session_state["finder_page"] == "upload":
        cv_file = upload_cv()
        st.markdown("Votre CV sera analysé par le modèle o4-min d'OpenAI.")
        if cv_file and ("keywords_domaine" not in st.session_state or "keywords_intitule" not in st.session_state or "cv_analysis" not in st.session_state):
            with st.spinner("🎯 Finder analyse votre CV pour vous proposer les offres d'emploi qui vous correspondent."):
                cv_progress = st.progress(0)
                keywords_domaine, keywords_intitule, analysis = get_keywords_from_cv(cv_file)
                cv_progress.progress(100)
            cv_progress.empty()
            if keywords_domaine and keywords_intitule and analysis:
                st.session_state["keywords_domaine"] = keywords_domaine
                st.session_state["keywords_intitule"] = keywords_intitule
                st.session_state["cv_analysis"] = analysis
        if "keywords_domaine" in st.session_state and "keywords_intitule" in st.session_state:
            placeholder_departement = "Sélectionnez un domaine"
            placeholder_intitule = "Sélectionnez un intitulé de métier"
            options_departement = [placeholder_departement] + st.session_state["keywords_domaine"]
            options_intitule = [placeholder_intitule] + st.session_state["keywords_intitule"]
            col1, col2 = st.columns(2)
            with col1:
                selected_departement = st.selectbox(
                    "Sélectionnez un domaine :",
                    options=options_departement,
                    index=0,
                    key="selected_departement",
                    on_change=lambda: st.session_state.update({"selected_intitule": placeholder_intitule}),
                )
            with col2:
                selected_intitule = st.selectbox(
                    "Sélectionnez un intitulé de métier :",
                    options=options_intitule,
                    index=0,
                    key="selected_intitule",
                    on_change=lambda: st.session_state.update({"selected_departement": placeholder_departement}),
                )
            st.info("Veuillez sélectionner soit un domaine, soit un intitulé de métier.")
            selection = None
            if selected_departement != placeholder_departement and selected_intitule != placeholder_intitule:
                st.error("Vous ne pouvez sélectionner qu'un seul mot, soit un domaine, soit un intitulé.")
            elif selected_departement != placeholder_departement:
                selection = selected_departement
            elif selected_intitule != placeholder_intitule:
                selection = selected_intitule
            if selection is None:
                st.warning("Veuillez effectuer une sélection avant de continuer.")
            else:
                if st.button("Trouver des offres d'emploi"):
                    display_advice()
                    df_offers = get_job_offers(selection)
                    if df_offers is not None:
                        df_offers = process_data(df_offers)
                        if df_offers is not None:
                            st.session_state["df_offers"] = df_offers
                            st.session_state["finder_page"] = "dashboard"
                            st.rerun()
    elif st.session_state["finder_page"] == "dashboard":
        if "df_offers" in st.session_state:
            display_dashboard(st.session_state["df_offers"])
    elif st.session_state["finder_page"] == "offers":
        if "filtered_df" in st.session_state:
            display_offers(st.session_state["filtered_df"])

elif selected == "Espace personnel":
    st.title("Espace personnel")
    st.write("Tableau de suivi de vos démarches")

# Fin du fichier
