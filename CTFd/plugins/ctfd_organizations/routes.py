"""
ctfd_organizations.routes
--------------------------
"""

import re

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from CTFd.models import Users, db
from CTFd.utils.decorators import admins_only, authed_only
from CTFd.utils.user import get_current_user

from .models import OrganizationMembers, Organizations

organizations_bp = Blueprint(
    "organizations",
    __name__,
    template_folder="templates",
    static_folder="static",
    url_prefix="/plugins/platform-plus",
)


def slugify(value: str) -> str:
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    return re.sub(r"[-\s]+", "-", value)


@organizations_bp.route("/organizations")
def organizations_list():
    orgs = Organizations.query.order_by(
        Organizations.verified.desc(), Organizations.name.asc()
    ).all()

    # Build per-org stats (members, teams, points) for cards + sidebar.
    org_stats = {}
    for org in orgs:
        member_rows = (
            db.session.query(OrganizationMembers, Users)
            .join(Users, OrganizationMembers.user_id == Users.id)
            .filter(OrganizationMembers.organization_id == org.id)
            .all()
        )
        member_count = len(member_rows)
        points = sum(user.get_score(admin=True) for _membership, user in member_rows)

        org_stats[org.id] = {
            "members": member_count,
            # No link between Organizations and CTFd Teams yet, so this
            # stays 0 until that relationship is added.
            "teams": 0,
            "points": points,
        }

    # Sidebar: top 3 organizations ranked by points (ties broken by name).
    top_organizations = sorted(
        orgs,
        key=lambda o: (-org_stats[o.id]["points"], o.name.lower()),
    )[:3]

    platform_stats = {
        "organizations": len(orgs),
    }

    return render_template(
        "platform_plus/organizations_list.html",
        organizations=orgs,
        org_stats=org_stats,
        top_organizations=top_organizations,
        platform_stats=platform_stats,
    )


@organizations_bp.route("/organizations/new", methods=["GET", "POST"])
@authed_only
def organizations_new():
    if request.method == "GET":
        return render_template("platform_plus/organizations_new.html")

    name = request.form.get("name", "").strip()
    org_type = request.form.get("org_type", "university")
    description = request.form.get("description", "").strip()
    website = request.form.get("website", "").strip()

    if not name:
        flash("Organization name is required.", "error")
        return redirect(url_for("organizations.organizations_new"))

    slug = slugify(name)
    if Organizations.query.filter_by(slug=slug).first():
        flash("An organization with a similar name is already registered.", "error")
        return redirect(url_for("organizations.organizations_new"))

    user = get_current_user()
    org = Organizations(
        name=name,
        slug=slug,
        org_type=org_type,
        description=description,
        website=website,
        owner_id=user.id,
    )
    db.session.add(org)
    db.session.flush()

    membership = OrganizationMembers(
        organization_id=org.id, user_id=user.id, role="owner"
    )
    db.session.add(membership)
    db.session.commit()

    flash("Organization created. Waiting for admin verification.", "success")
    return redirect(url_for("organizations.organization_detail", slug=org.slug))


@organizations_bp.route("/organizations/<slug>")
def organization_detail(slug):
    org = Organizations.query.filter_by(slug=slug).first_or_404()
    members = (
        db.session.query(OrganizationMembers, Users)
        .join(Users, OrganizationMembers.user_id == Users.id)
        .filter(OrganizationMembers.organization_id == org.id)
        .all()
    )
    return render_template(
        "platform_plus/organization_detail.html", org=org, members=members
    )


@organizations_bp.route("/organizations/<slug>/join", methods=["POST"])
@authed_only
def organization_join(slug):
    org = Organizations.query.filter_by(slug=slug).first_or_404()
    user = get_current_user()

    existing = OrganizationMembers.query.filter_by(
        organization_id=org.id, user_id=user.id
    ).first()
    if existing:
        flash("You are already a member of this organization.", "info")
        return redirect(url_for("organizations.organization_detail", slug=slug))

    membership = OrganizationMembers(
        organization_id=org.id, user_id=user.id, role="member"
    )
    db.session.add(membership)
    db.session.commit()
    flash("Successfully joined the organization.", "success")
    return redirect(url_for("organizations.organization_detail", slug=slug))


@organizations_bp.route("/admin/organizations/<int:org_id>/verify", methods=["POST"])
@admins_only
def organization_verify(org_id):
    org = Organizations.query.get_or_404(org_id)
    org.verified = True
    db.session.commit()
    return jsonify({"success": True})

# admin-facing UI
@organizations_bp.route("/admin/organizations")
@admins_only
def organizations_admin_list():
    pending = Organizations.query.filter_by(verified=False).order_by(
        Organizations.created_at.asc()
    ).all()
    return render_template("platform_plus/organizations_admin.html", pending=pending)

@organizations_bp.route("/admin/organizations/<int:org_id>/reject", methods=["POST"])
@admins_only
def organization_reject(org_id):
    org = Organizations.query.get_or_404(org_id)
    OrganizationMembers.query.filter_by(organization_id=org.id).delete()
    db.session.delete(org)
    db.session.commit()
    return jsonify({"success": True})