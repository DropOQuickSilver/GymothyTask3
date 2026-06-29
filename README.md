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
 - Personal record tracking
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


  Gymothy also has an admin debug page for inspecting database records. To make an account an admin, first create an account through the stardard 
  sign up page. Then:
    1. open terminal
    2. run "from app import app, db, User
            app.app_context().push()
            user = User.query.filter_by(username="ajpayj111").first()
            user.is_admin = True
            db.session.commit()"
    3. Now restart the app again and login
    4. The admin debug page can be accessed at /admin/debug that can only be accessed through an admin account

            
