This is my Software Engineering Task 3 project 
My project is called "Gymothy" and is a diet and workout tracker app, and to also utilize ML to give feedback and predict progress! It aims to combine workout tracking and meal tracking into one, simple app! Through utilizing machine learning, you can have your progress visualised!

Gymothy has been deployed live through Render!
Live app: https://gymothytask3.onrender.com

Main Features:
 - User registration and login
 - Secure password hashing using Flask-Bcrypt
 - User session management using Flask-Login
 - Workout session creation, viewing, editing and deletion
 - Exercise logging with sets, reps, weight and RPE
 - Meal and macro tracking
 - Admin/debug page for database inspection
 - Role-based admin access
 - Input validation using Flask-WTF and WTForms
 - Machine learning strength prediction feature
 - 3-week projected max calculation
 - Strength trend graph with recent estimated maxes and projected progress
 - Render deployment using Gunicorn

Tech Stack: 
 - Python
 - Flask
 - Flask-SQLAlchemy
 - SQLite
 - Flask-Login
 - Flask-WTF
 - WTForms
 - Flask-Bcrypt
 - scikit-learn
 - pandas
 - numpy
 - joblib
 - Gunicorn
 - HTML
 - CSS
 - Jinja2
 - Render

Machine Learning Feature: 
  Gymothy includes a progress prediction visualisation feature, that uses machine learning to predict progress over a 3 week span. It uses past user    given data such as estimated 1rm, volume, average RPE in order to calculate a predicted future 1rm!


Local Setup Instructions:
  1. install python 3.11 or later
  2. Clone the repository, git clone https://github.com/DropOQuickSilver/GymothyTask3.git
                           cd GymothyTask3
  3. Create a virtual environment,
     For macOS/Linux:
         python3 -m venv .venv
         source .venv/bin/activate

     For Windows:
         python -m venv .venv
         .venv\Scripts\activate
  4. Install dependencies: pip install -r requirements.txt
  5. Train the machine learning model: python -m ml.train_model
  6. Run the app locally: python app.py
     Then open the app in your browser:
          http://localhost:5000
      or:
          http://127.0.0.1:5000


Admin Setup:
Gymothy includes a protected admin/debug page for inspecting database records during development. This page is only accessible to users with admin permissions.
To create an admin account:
 1. First register a normal account through the Gymothy sign-up page. After the account has been created, open the project folder in Terminal and start Python:
 2. from app import create_app
    from extensions import db
    from models import User
    
    app = create_app()
    
    with app.app_context():
       user = User.query.filter_by(username="YOUR_USERNAME").first()
   
       if user:
           user.is_admin = True
           user.role = "admin"
           db.session.commit()
           print(f"{user.username} has been promoted to admin.")
       else:
           print("User not found. Make sure the account has been created first.")

    Replacing YOUR_USERNAME with the account name

3. Then to access the admin page, type the url "/admin/debug


GymothyTask3/
│
├── app.py                    # Main Flask application factory and dashboard routes
├── extensions.py             # Shared Flask extensions
├── models.py                 # SQLAlchemy database models
├── forms.py                  # Flask-WTF form classes and validators
├── utils.py                  # Helper functions
├── backup_database.py        # Timestamped database backup script
├── requirements.txt          # Python dependencies
│
├── routes/                   # Modular Flask blueprints
│   ├── auth_routes.py
│   ├── session_routes.py
│   ├── meal_routes.py
│   ├── pr_routes.py
│   ├── prediction_routes.py
│   └── admin_routes.py
│
├── ml/                       # Machine learning files
│   ├── strength_predictor.py
│   └── train_model.py
│
├── templates/                # Jinja2 HTML templates
├── static/                   # CSS and static assets
└── backups/                  # Database backup output folder
