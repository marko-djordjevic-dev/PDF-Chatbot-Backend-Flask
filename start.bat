flask db init
flask db migrate -m "initial"
flask db upgrade
flask run
gunicorn -w 4 run:app