import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    clerk_org_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    hubspot_api_key: Mapped[str | None] = mapped_column(Text)  # encrypted at rest via secrets manager
    plan: Mapped[str] = mapped_column(Text, default="free")  # free | pro | enterprise
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    users: Mapped[list["User"]] = relationship(back_populates="org", cascade="all, delete-orphan")
    jobs: Mapped[list["Job"]] = relationship(back_populates="org", cascade="all, delete-orphan")
    field_mappings: Mapped[list["HubSpotFieldMapping"]] = relationship(back_populates="org", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    clerk_user_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(Text, default="reviewer")  # admin | reviewer | viewer
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    org: Mapped["Organization"] = relationship(back_populates="users")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    uploaded_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    original_filename: Mapped[str] = mapped_column(Text, nullable=False)
    s3_key: Mapped[str] = mapped_column(Text, nullable=False)
    doc_type: Mapped[str] = mapped_column(Text, nullable=False)  # tax_return | government_id | bank_statement | general
    status: Mapped[str] = mapped_column(Text, default="pending")
    # pending → queued → ocr → extracting → validating → review_queue | crm_pending → crm_written | error
    celery_task_id: Mapped[str | None] = mapped_column(Text)
    page_count: Mapped[int | None] = mapped_column(Integer)
    ocr_text: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    crm_contact_id: Mapped[str | None] = mapped_column(Text)
    processing_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    org: Mapped["Organization"] = relationship(back_populates="jobs")
    extraction: Mapped["Extraction | None"] = relationship(back_populates="job", uselist=False, cascade="all, delete-orphan")
    flags: Mapped[list["ValidationFlag"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    review: Mapped["ReviewQueue | None"] = relationship(back_populates="job", uselist=False, cascade="all, delete-orphan")
    audit_entries: Mapped[list["AuditLog"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    crm_log: Mapped["CRMLog | None"] = relationship(back_populates="job", uselist=False, cascade="all, delete-orphan")


class Extraction(Base):
    __tablename__ = "extractions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), unique=True, nullable=False)
    doc_type: Mapped[str] = mapped_column(Text, nullable=False)
    raw_fields: Mapped[dict] = mapped_column(JSONB, nullable=False)
    confidence: Mapped[dict] = mapped_column(JSONB, nullable=False)  # {field: "high"|"medium"|"low"|"not_found"}
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    job: Mapped["Job"] = relationship(back_populates="extraction")


class ValidationFlag(Base):
    __tablename__ = "validation_flags"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    flag_type: Mapped[str] = mapped_column(Text, nullable=False)  # MISSING_REQUIRED | OUT_OF_RANGE | FORMAT_MISMATCH | CROSS_FIELD
    field_name: Mapped[str | None] = mapped_column(Text)
    plain_message: Mapped[str] = mapped_column(Text, nullable=False)  # Human-readable, shown to reviewer
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    job: Mapped["Job"] = relationship(back_populates="flags")


class ReviewQueue(Base):
    __tablename__ = "review_queue"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), unique=True, nullable=False)
    assigned_to: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_fields: Mapped[dict | None] = mapped_column(JSONB)  # staff corrections
    review_status: Mapped[str] = mapped_column(Text, default="pending")  # pending | approved | rejected
    reviewed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reject_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    job: Mapped["Job"] = relationship(back_populates="review")


class HubSpotFieldMapping(Base):
    __tablename__ = "hubspot_field_mapping"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    doc_type: Mapped[str] = mapped_column(Text, nullable=False)  # one row per doc_type per org
    mapping: Mapped[dict] = mapped_column(JSONB, nullable=False)  # {"taxpayer_name": "firstname", ...}
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    org: Mapped["Organization"] = relationship(back_populates="field_mappings")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    job_id: Mapped[str | None] = mapped_column(ForeignKey("jobs.id", ondelete="SET NULL"))
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    actor: Mapped[str] = mapped_column(Text, default="System")  # display name for UI
    action: Mapped[str] = mapped_column(Text, nullable=False)
    # UPLOADED | OCR_COMPLETE | EXTRACTED | VALIDATION_PASSED | FLAGGED |
    # REVIEWED | APPROVED | REJECTED | CRM_WRITTEN | FIELD_CHANGED | ERROR
    detail: Mapped[dict | None] = mapped_column(JSONB)  # {field, before, after} for FIELD_CHANGED
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    job: Mapped["Job | None"] = relationship(back_populates="audit_entries")


class CRMLog(Base):
    __tablename__ = "crm_log"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), unique=True, nullable=False)
    crm_contact_id: Mapped[str | None] = mapped_column(Text)
    crm_response: Mapped[dict | None] = mapped_column(JSONB)
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    job: Mapped["Job"] = relationship(back_populates="crm_log")
