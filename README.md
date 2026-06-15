This is my Software Engineering Task 3 project 
My project is called "Gymothy" and is a diet and workout tracker app, and to also utilize ML to give feedback and predict progress!

How to set up to run locally:
  1. install python
  2. Open project folder through example "cd \Users\example\Documents\Github\Gymothy"
  3. run "python -m venv venv" then ".\venv\Scripts\Activate"
  4. Then to install Flask and SQL on your machine then run "pip install flask flask-sqlalchemy flask-login flask-wtf wtforms flask-bcrypt"
  5. Ensure all the code looks correct and matches
  6. run "python app.py" to start the app
  7. Then go to your browser and type "localhost:5000", taking you to your app!

Have Fun!!!

  To make a certain account admin, follow these steps (for an existing account)!
    1. open terminal
    2. run "from app import app, db, User
            app.app_context().push()
            
            user = User.query.filter_by(username="ajpayj111").first()
            user.is_admin = True
            db.session.commit()"
    3. Now start the app again and login
    4. You are now an admin account
    5. If you want to access the admin debug page, change the url to "/admin/debug"

  Now enjoy!
            
