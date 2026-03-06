# PSC Official Website

A modern, responsive Flask web application for the Pen Stealing Company (PSC) - a revolutionary stationary company founded in 2025.

## Features

- **User Authentication**: Secure login and registration system with Flask-Login
- **Modern UI**: Neon/futuristic design with responsive layout
- **Database Integration**: SQLite database with SQLAlchemy ORM
- **Company Pages**: About page, partnerships, and contact information
- **Interactive Design**: Gradient animations and hover effects

## Tech Stack

- **Backend**: Python Flask
- **Database**: SQLite with SQLAlchemy
- **Authentication**: Flask-Login
- **Frontend**: HTML5, CSS3, JavaScript
- **Styling**: Custom CSS with Orbitron font

## Installation

1. Clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/psc-official.git
cd psc-official
```

2. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
python app.py
```

5. Open your browser and navigate to `http://localhost:5000`

## Project Structure

```
psc-official/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── static/
│   └── logo.png          # Company logo
└── templates/
    ├── index.html        # Homepage
    ├── login.html        # Login page
    ├── signup.html       # Registration page
    └── about.html        # About page
```

## Features Overview

### Authentication System
- User registration with username, password, and additional profile information
- Secure login/logout functionality
- Session management with Flask-Login

### Modern UI Design
- Neon color scheme with green (#09ff00) and purple (#ba19eb) accents
- Responsive design that works on desktop, tablet, and mobile
- Interactive elements with hover effects and animations
- Orbitron font for a futuristic look

### Database Schema
- User table with authentication and profile information
- SQLite database for easy deployment

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## About PSC

The Pen Stealing Company (PSC) is dedicated to revolutionizing the stationary industry through innovation and quality. Founded in 2025, PSC combines creativity with technology to deliver exceptional writing experiences.

---

*Built with ❤️ for the future of stationary*