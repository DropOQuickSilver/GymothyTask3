from flask import Blueprint, render_template, request, flash, redirect, url_for, abort
from flask_login import login_required, current_user

from extensions import db
from forms import MealForm, DeleteForm
from models import Meal

meal_bp = Blueprint("meal", __name__)


@meal_bp.route("/add-meal", methods=["GET", "POST"])
@login_required
def add_meal():
    form = MealForm()

    if form.validate_on_submit():
        new_meal = Meal()
        new_meal.meal_name = form.meal_name.data
        new_meal.calories = form.calories.data
        new_meal.protein = form.protein.data
        new_meal.carbs = form.carbs.data
        new_meal.fats = form.fats.data
        new_meal.user_id = current_user.id

        db.session.add(new_meal)
        db.session.commit()

        flash("Meal added successfully.", "meal")
        return redirect(url_for("meal.macros"))

    return render_template("add_meal.html", form=form)


@meal_bp.route("/meal/<int:meal_id>/edit", methods=["GET", "POST"])
@login_required
def edit_meal(meal_id):
    meal = Meal.query.filter_by(
        id=meal_id,
        user_id=current_user.id,
    ).first()

    if meal is None:
        abort(404)

    form = MealForm(obj=meal)

    if form.validate_on_submit():
        meal.meal_name = form.meal_name.data
        meal.calories = form.calories.data
        meal.protein = form.protein.data
        meal.carbs = form.carbs.data
        meal.fats = form.fats.data

        db.session.commit()

        flash("Meal updated successfully.")
        return redirect(url_for("meal.macros"))

    return render_template(
        "edit_meal.html",
        form=form,
        meal=meal,
    )


@meal_bp.route("/meal/<int:meal_id>/delete", methods=["POST"])
@login_required
def delete_meal(meal_id):
    delete_form = DeleteForm()

    if not delete_form.validate_on_submit():
        abort(400)

    meal = Meal.query.filter_by(
        id=meal_id,
        user_id=current_user.id,
    ).first()

    if meal is None:
        abort(404)

    db.session.delete(meal)
    db.session.commit()

    flash("Meal deleted successfully.", "meal")
    return redirect(url_for("meal.macros"))


@meal_bp.route("/macros")
@login_required
def macros():
    meals = (
        Meal.query.filter_by(user_id=current_user.id)
        .order_by(Meal.id.desc())
        .all()
    )

    total_calories, total_protein, total_carbs, total_fats = (
        db.session.query(
            db.func.coalesce(db.func.sum(Meal.calories), 0),
            db.func.coalesce(db.func.sum(Meal.protein), 0),
            db.func.coalesce(db.func.sum(Meal.carbs), 0),
            db.func.coalesce(db.func.sum(Meal.fats), 0),
        )
        .filter(Meal.user_id == current_user.id)
        .one()
    )

    delete_form = DeleteForm()

    return render_template(
        "macros.html",
        meals=meals,
        total_calories=total_calories,
        total_protein=total_protein,
        total_carbs=total_carbs,
        total_fats=total_fats,
        delete_form=delete_form,
    )
