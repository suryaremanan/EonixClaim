# EonixClaim

[![Python Version](https://img.shields.io/badge/python-3.9-blue.svg)](https://www.python.org/downloads/release/python-390/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

EonixClaim is a comprehensive InsurTech platform that revolutionizes the vehicle insurance claims process by combining computer vision, telematics, AI/ML, blockchain, and conversational interfaces.

## 🌟 Features

- **Automated Damage Assessment**: Analyzes vehicle damage from photos using YOLOv8
- **Telematics Integration**: Leverages real driving data to personalize premiums and validate claims
- **Fraud Detection**: Uses AI/ML to identify potentially fraudulent claims
- **Blockchain Records**: Maintains tamper-proof records of all claims and transactions
- **Slack Interface**: Provides an intuitive conversational interface for customers
- **Salesforce Integration**: Streamlines agent workflows and customer communications

## 🛠️ Technologies

- **Core**: Python 3.9
- **Image Processing**: YOLOv8 with PyTorch
- **Data Analysis**: NumPy, Pandas
- **CRM**: Salesforce API (via simple_salesforce)
- **User Interface**: Slack API with Block Kit
- **Blockchain**: Ethereum (Web3)
- **Machine Learning**: scikit-learn, TensorFlow
- **Database**: SQLite for local development
- **Containerization**: Docker

## 📋 Prerequisites

- Python 3.9+
- Docker (optional, for containerized deployment)
- Slack workspace with admin privileges
- Salesforce developer account
- Ethereum wallet (for blockchain features)

## 🚀 Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/suryaremanan/EonixClaim.git
   cd EonixClaim
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   ```bash
   cp .env.example .env
   ```
   Edit the `.env` file to include your credentials and configuration.

5. **Initialize the database**:
   ```bash
   python database/init_db.py
   ```

## ⚙️ Configuration

EonixClaim requires several API keys and configuration options set in the `.env` file:

- **YOLO Configuration**: Path to model and confidence threshold
- **Telematics Settings**: Data path and risk thresholds
- **Email Configuration**: SMTP server settings
- **Salesforce Credentials**: API access tokens and instance URL
- **Blockchain Settings**: Ethereum provider URL and contract address
- **Slack Credentials**: Bot token, signing secret, and app token

## 📱 Usage

### Starting the Application

```bash
python app.py
```

