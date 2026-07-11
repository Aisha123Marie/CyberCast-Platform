"""
ctfd_organizations.models
--------------------------
University / company / community collaboration spaces.
"""

import datetime

from CTFd.models import db


class Organizations(db.Model):
    __tablename__ = "org_organizations"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, unique=True)
    slug = db.Column(db.String(128), nullable=False, unique=True)
    org_type = db.Column(
        db.String(32), default="university"
    )  # university | company | community
    description = db.Column(db.Text)
    website = db.Column(db.String(256))
    logo_url = db.Column(db.String(256))
    verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))

    members = db.relationship(
        "OrganizationMembers", backref="organization", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Organization {self.name} ({self.org_type})>"


class OrganizationMembers(db.Model):
    __tablename__ = "org_organization_members"

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey("org_organizations.id", ondelete="CASCADE")
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"))
    role = db.Column(db.String(32), default="member")  # owner | admin | member
    joined_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    status = db.Column(db.String(32), default="pending")  # pending | approved | rejected
    __table_args__ = (
        db.UniqueConstraint("organization_id", "user_id", name="uq_org_user"),
    )
