# finder
Persionnalized and reasonning job application

Application à visée pédagogique et non commerciale.

Un cv data ou dev vous permettra d'exploiter toutes les fonctionalités de finder.
Si besoin, vous pouvez utiliser le CV anonyme à disposition dans le repo.

La collecte de données est effectuée via un appel API sur le site de France Travail.
Les données collectées sont nettoyées et traitées via Pandas.
Les fonctionnalités d'intelligence de Finder reposent sur des appels API OpenAI, modèle 4o-mini via un travail de prompt engineering.


https://finder.streamlit.app/

🎯 Finder - Analyse de CV et Recommandation d'Offres d'Emploi

Finder est une application web développée avec Streamlit, permettant aux utilisateurs d'uploader leur CV en PDF ou DOCX afin d'obtenir des recommandations d'offres d'emploi pertinentes via un appel API vers le serveur de France Travail. 
L'application intègre également un tableau de bord interactif, une génération automatique de lettres de motivation, des préparations à l'entretien d'embauche via une API d'IA générative.

![Capture d'écran 2025-03-06 211106](https://github.com/user-attachments/assets/bb5ebb4b-d0fb-4f31-8636-0a1410cce260)

![Capture d'écran 2025-03-06 190908](https://github.com/user-attachments/assets/33d4b00a-d68c-454d-b9f6-227cc61ae369)


Fonctionnalités:

- Upload de CV : Analyse automatique des compétences et expériences du candidat.
- Recommandation d'offres : Correspondance entre le profil du candidat et des offres d'emploi.
- Génération de lettre de motivation : Création d'une lettre personnalisée basée sur le CV et l'offre choisie.
- Tableau de bord interactif : Visualisation des recommandations et statistiques sur les offres.
- Préparation à l'entretien d'embauche
- Préparation aux tests techniques

![Capture d'écran 2025-03-06 204136](https://github.com/user-attachments/assets/aaff1dac-2495-420e-9ea4-5ca7c2fc1a59)

![Capture d'écran 2025-03-06 190553](https://github.com/user-attachments/assets/e8944183-56a6-453a-8676-37e9b7e3fc73)

Technologies utilisées

    Python 🐍
    Streamlit 🎨 (Interface utilisateur)
    Pandas 📊 (Traitement des données)
    API IA générative 🤖 (Création automatique de lettres de motivation, entretiens, chatbot)
    API France Travail

L'application finder a été développée dans le cadre d'un projet de fin de formation à la Wild Code School de Lille. Ce travail a été réalisé en équipe, merci à Ludovic, Riad et Daniel pour leur investissement et leur bonne humeur ! Merci à nos formateurs Soufiane et Tiphaine pour leurs précieux conseils !
