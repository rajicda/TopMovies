from datetime import datetime
from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Float
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FloatField
from wtforms.validators import DataRequired, NumberRange
import requests

app = Flask(__name__)
app.config['SECRET_KEY'] = 'Anything'
Bootstrap5(app)
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///movies-collection.db"

MOVIES = "https://api.themoviedb.org/3/search/movie"
MOVIES_BY_ID = "https://api.themoviedb.org/3/movie"
API_TOKEN = "<TOKEN>"
headers = {
    "Authorization": API_TOKEN
}


class Base(DeclarativeBase):
    pass


# Create the extension
db = SQLAlchemy(model_class=Base)
# Initialise the app with the extension
db.init_app(app)


# CREATE TABLE
class Movie(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    rating: Mapped[float] = mapped_column(Float, nullable=False)
    ranking: Mapped[int] = mapped_column(Integer, nullable=True)
    review: Mapped[str] = mapped_column(String(250), nullable=True)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)

    # Optional: this will allow each book object to be identified by its title when printed.
    # def __repr__(self):
    #     return f'<Book {self.title}>'


# Create table schema in the database. Requires application context.
with app.app_context():
    db.create_all()


class RateMovieForm(FlaskForm):
    rating: int = FloatField('Your Rating Out of 10 e.g. 7.5', validators=[DataRequired(), NumberRange(min=0, max=10, message='Rating must be between 0 and 10')])
    review: str = StringField('Your Review', validators=[DataRequired()])
    submit = SubmitField('Update Movie!')


class AddMovieForm(FlaskForm):
    title: str = StringField('Movie Title', validators=[DataRequired()])
    submit = SubmitField('Add Movie!')


def get_movies_by_title(query: dict) -> dict:
    return requests.get(url=MOVIES, params=query, headers=headers).json()


def get_movies_by_id(id: str) -> dict:
    return requests.get(url=MOVIES_BY_ID + "/" + id, headers=headers).json()


@app.route("/")
def home():
    # READ RECORD
    # Add to DB
    # with app.app_context():
    #     second_movie = Movie(
    #         title="Avatar The Way of Water",
    #         year=2022,
    #         description="Set more than a decade after the events of the first film, learn the story of the Sully family (Jake, Neytiri, and their kids), the trouble that follows them, the lengths they go to keep each other safe, the battles they fight to stay alive, and the tragedies they endure.",
    #         rating=7.3,
    #         ranking=9,
    #         review="I liked the water.",
    #         img_url="https://image.tmdb.org/t/p/w500/t6HIqrRAclMCA60NsSmeqe9RmNV.jpg"
    #     )
    #     db.session.add(second_movie)
    #     db.session.commit()
    with app.app_context():
        result = db.session.execute(db.select(Movie).order_by(Movie.rating.asc()))
        all_movies = result.scalars().fetchall()
        for i in range(len(all_movies)):
            all_movies[i].ranking = len(all_movies) - i
            db.session.commit()
        return render_template("index.html", all_movies=all_movies)


@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_movie(id):
    # EDIT MOVIE
    edit_form = RateMovieForm()
    with app.app_context():
        movie_to_update = db.session.execute(db.select(Movie).where(Movie.id == id)).scalar()
    if request.method == 'POST':
        if not edit_form.validate_on_submit():
            return render_template('edit.html', edit_form=edit_form, movie=movie_to_update)
        elif edit_form.is_submitted() and edit_form.validate_on_submit():
            # UPDATE RECORD
            with app.app_context():
                movie_to_update = db.session.execute(db.select(Movie).where(Movie.id == id)).scalar()
                movie_to_update.rating = edit_form.rating.data
                movie_to_update.review = edit_form.review.data
                db.session.commit()
        return redirect(url_for('home'))
    else:
        return render_template('edit.html', edit_form=edit_form, movie=movie_to_update)


@app.route("/add", methods=["GET", "POST"])
def add_movie():
    # ADD MOVIE
    add_form = AddMovieForm()
    if request.method == 'POST':
        if add_form.validate_on_submit():
            query = {
                "query": add_form.title.data
            }
            found_movies = get_movies_by_title(query)
            return render_template('select.html', add_form=add_form, movies=found_movies)
    return render_template('add.html', add_form=add_form)


@app.route("/select/<int:id>", methods=["GET", "POST"])
def select_movie(id):
    # SELECT AND ADD MOVIE
    movie_details = get_movies_by_id(str(id))
    with app.app_context():
        year = datetime.strptime(movie_details.get('release_date'), "%Y-%m-%d").strftime("%Y")
        new_movie = Movie(
                title=movie_details.get('title'),
                year=year,
                description=movie_details.get('overview'),
                rating=round(movie_details.get('vote_average'), 1),
                img_url=f"https://image.tmdb.org/t/p/w500/{movie_details.get('backdrop_path')}"
            )
        db.session.add(new_movie)
        db.session.commit()
        return redirect(url_for('edit_movie', id=new_movie.id))


@app.route("/delete/<int:id>", methods=["GET"])
def delete_movie(id):
    # DELETE MOVIE
    with app.app_context():
        movie_to_delete = db.session.execute(db.select(Movie).where(Movie.id == id)).scalar()
        db.session.delete(movie_to_delete)
        db.session.commit()
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)
