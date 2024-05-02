# Project Repository Overview

This repository is designed as a comprehensive suite for a machine learning bootcamp course, containing a range of training exercises, capstone projects, and related resources. Below is a detailed overview of the repository contents, structured to facilitate a hands-on learning experience with diverse tools and techniques in machine learning.

## Table of Contents
1. [Daily Exercises](#daily-exercises)
2. [Capstone Projects](#capstone-projects)
3. [Supporting Files and Directories](#supporting-files-and-directories)
4. [Setup and Configuration](#setup-and-configuration)
5. [License](#license)
6. [Contact Information](#contact-information)

## Daily Exercises
This section provides practical experience with different machine learning tasks and tools through various exercises.

### 1.1 Finetuning Exercise
- **Data**: Datasets for model fine-tuning.
- **Notebooks**: Jupyter notebooks with detailed instructions for data preparation and model tuning.

### 1.2 Langchain Introduction
- **Configurations and Data**: Configuration files and sample datasets.
- **Images and Notebooks**: Tutorial resources including images and notebooks on Langchain basics.

### 1.3 RAG Exercise
- **Data and Scripts**: Resources for the Retrieval-Augmented Generation (RAG) exercise.
- **Notebooks**: Detailed process walkthrough in Jupyter notebooks.

### 1.4 Synthetic Data Exercise
- **Data and Scripts**: Tools and datasets for synthetic data manipulation.
- **Notebooks**: Demonstrations on synthetic data handling.

## Capstone Projects
Designed to integrate skills from the course into substantial, real-world data science tasks.

### 2.1 Vector Database
- **Notebooks**: Guides on document embeddings and vector databases.
- **Scripts**: Tools for embedding generation and database queries.

### 2.2 RAG Prompt Engineering
- **Data and Notebooks**: Advanced exercises on RAG for prompt engineering.
- **Scripts**: Support scripts for RAG operations.

### 2.3 Finetuning for RAG
- **Notebooks**: Comprehensive guides on fine-tuning for retrieval-augmented tasks.
- **Scripts**: Training and operational scripts.

### 2.4 Inference Methods
- **Notebooks and Scripts**: Resources on various inference methods, including practical applications.

### 2.5 Solution Directory
- **Purpose**: Completed examples and solutions as references for learners.

## Supporting Files and Directories
- **`data/`**: Datasets for multiple projects.
- **`docker-compose.yml`**: Setup for required Docker containers.
- **`environment.yml`, `locked-environment.yml`**: Environment setup files.
- **`setup.sh`**: Script for initializing the development environment.

## Setup and Configuration

### Setup.py
Automates the environment setup necessary for the machine learning course. **This has already been done for you**.
1. **Loads Configurations**: Reads `company.yml` if available, to set environment variables.
2. **Updates and Installs**: Installs essential tools and updates software lists.
3. **Sets Up Python and Jupyter Notebook**: Installs Miniconda and configures Jupyter.
4. **Docker Services**: Details the setup of a PGVector database via Docker Compose. For more information on integrating PGVector with Langchain, visit the [Langchain PGVector integration documentation](https://python.langchain.com/docs/integrations/vectorstores/pgvector/).

## License
This project is released under the [Apache 2.0 License](https://www.apache.org/licenses/LICENSE-2.0), which details how the materials can be used, modified, and shared.

## Contact Information
For support or questions, please contact us at Henderson dot Johnson dot i i at Accenture dot com.

This repository is equipped with everything from basic exercises to complex projects to help users grasp complex concepts through practical implementation.