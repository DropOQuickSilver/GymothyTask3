from flask import Blueprint, render_template, request, flash, redirect, url_for, abort
from flask_login import login_required, current_user

from extensions import db
from forms import PersonalRecordForm, DeleteForm
from models import PersonalRecord

pr_bp = Blueprint("pr", __name__)


@pr_bp.route("/prs")
@login_required
def prs():
    personal_records = (
        PersonalRecord.query.filter_by(user_id=current_user.id)
        .order_by(PersonalRecord.id.desc())
        .all()
    )

    delete_form = DeleteForm()

    return render_template(
        "prs.html",
        personal_records=personal_records,
        delete_form=delete_form,
    )


@pr_bp.route("/pr/new", methods=["GET", "POST"])
@login_required
def new_pr():
    form = PersonalRecordForm()

    if form.validate_on_submit():
        new_record = PersonalRecord()
        new_record.lift_name = form.lift_name.data
        new_record.weight = form.weight.data
        new_record.user_id = current_user.id

        db.session.add(new_record)
        db.session.commit()

        flash("Personal record added successfully.")
        return redirect(url_for("pr.prs"))

    return render_template("new_pr.html", form=form)


@pr_bp.route("/pr/<int:pr_id>/edit", methods=["GET", "POST"])
@login_required
def edit_pr(pr_id):
    personal_record = PersonalRecord.query.filter_by(
        id=pr_id,
        user_id=current_user.id,
    ).first()

    if personal_record is None:
        abort(404)

    form = PersonalRecordForm(obj=personal_record)

    if form.validate_on_submit():
        personal_record.lift_name = form.lift_name.data
        personal_record.weight = form.weight.data

        db.session.commit()

        flash("Personal record updated successfully.")
        return redirect(url_for("pr.prs"))

    return render_template(
        "edit_pr.html",
        form=form,
        personal_record=personal_record,
    )


@pr_bp.route("/pr/<int:pr_id>/delete", methods=["POST"])
@login_required
def delete_pr(pr_id):
    delete_form = DeleteForm()

    if not delete_form.validate_on_submit():
        abort(400)

    personal_record = PersonalRecord.query.filter_by(
        id=pr_id,
        user_id=current_user.id,
    ).first()

    if personal_record is None:
        abort(404)

    db.session.delete(personal_record)
    db.session.commit()

    flash("Personal record deleted successfully.")
    return redirect(url_for("pr.prs"))
