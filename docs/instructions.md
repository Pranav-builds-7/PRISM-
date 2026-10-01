# PRISM – Project Instructions

PRISM is an AI-powered logistics intelligence system designed to improve supply chain visibility, predict delivery risks, and support operational decision-making.

## Project Workflow

1. **Data Ingestion:** Load raw logistics data from CSV files into a legacy MySQL database.
2. **ETL Pipeline:** Use Apache Airflow to clean, transform, and process logistics data.
3. **Machine Learning:** Predict shipment delays and identify potential logistics risks.
4. **RAG & Vector Database:** Store and retrieve logistics SOPs and operational documents for context-aware responses.
5. **AI Agent:** Integrate LLMs, SQL queries, and RAG to analyze logistics operations and provide recommendations.
6. **Backend:** Build APIs using FastAPI to connect the AI system with the application.
7. **Dashboard:** Develop a Streamlit dashboard for logistics monitoring and insights.
8. **Deployment:** Containerize the application with Docker and deploy it on AWS EC2.

## Main Technologies

* Python
* MySQL
* Apache Airflow
* Pandas and Scikit-learn
* LangChain / LangGraph
* Vector Database
* FastAPI
* Streamlit
* Docker
* AWS EC2

## Goal

Build a practical, scalable logistics AI system that combines data engineering, machine learning, and generative AI to assist logistics teams with real-time insights and decision support.

**Note:** This project is being developed in phases. Some components are planned and are not yet implemented.
