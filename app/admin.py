from calendar import monthrange
from datetime import date, datetime, timedelta
from html import escape
import io
from pathlib import Path
from string import Template
import csv

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_admin
from app.payment_metadata import build_payment_metadata
from app.models import (
    Attendance,
    Booking,
    Center,
    CenterMembership,
    FitnessClass,
    InstructorProfile,
    Member,
    Membership,
    NotificationDeliveryAttempt,
    NotificationRequest,
    Payment,
)
from app.reminders import queue_membership_expiry_reminders
from app.notification_dispatch import process_pending_notifications
from app.bookings import promote_waitlist_for_available_seats

router = APIRouter(prefix="/admin")
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
MIN_RISK_DAYS = 14
MAX_RISK_DAYS = 180
MIN_RISK_THRESHOLD_PCT = 0.0
MAX_RISK_THRESHOLD_PCT = 100.0


def _render_weekly_report_html(payload: dict) -> str:
    template = (TEMPLATES_DIR / "weekly_performance_report.html").read_text(
        encoding="utf-8"
    )
    metrics = payload.get("metrics", {})
    revenue = metrics.get("revenue", {})
    member_growth = metrics.get("member_growth", {})
    occupancy = metrics.get("occupancy", {})
    at_risk = metrics.get("at_risk", {})
    highlights = payload.get("highlights", {})
    period = payload.get("period", {})
    scope = payload.get("scope", {})

    substitutions = {
        "report_title": escape(str(payload.get("title", "Weekly Performance Report"))),
        "scope_label": escape(str(scope.get("label", "Global Admin"))),
        "period_start": escape(str(period.get("start", ""))),
        "period_end": escape(str(period.get("end", ""))),
        "generated_at": escape(str(payload.get("generated_at", ""))),
        "revenue_total": f"{float(revenue.get('total_amount', 0.0)):.2f}",
        "revenue_delta_pct": f"{float(revenue.get('change_vs_previous_week_pct', 0.0)):.2f}",
        "highlight_revenue": escape(str(highlights.get("revenue", ""))),
        "member_new": str(int(member_growth.get("new_members", 0))),
        "member_base": str(int(member_growth.get("member_base", 0))),
        "retention_rate": f"{float(member_growth.get('retention_rate', 0.0)):.2f}",
        "highlight_member": escape(str(highlights.get("member_growth_retention", ""))),
        "classes_count": str(int(occupancy.get("classes_count", 0))),
        "booked_total": str(int(occupancy.get("booked_total", 0))),
        "fill_rate": f"{float(occupancy.get('fill_rate', 0.0)):.2f}",
        "highlight_occupancy": escape(str(highlights.get("class_occupancy", ""))),
        "at_risk_count": str(int(at_risk.get("count", 0))),
        "at_risk_pct": f"{float(at_risk.get('share_of_active_members_pct', 0.0)):.2f}",
        "highlight_risk": escape(str(highlights.get("at_risk", ""))),
    }
    return Template(template).safe_substitute(substitutions)


def _validate_member_risk_params(days: int, threshold_pct: float) -> None:
    if days < MIN_RISK_DAYS or days > MAX_RISK_DAYS:
        raise HTTPException(
            status_code=400,
            detail=f"Days must be between {MIN_RISK_DAYS} and {MAX_RISK_DAYS}",
        )
    if threshold_pct < MIN_RISK_THRESHOLD_PCT or threshold_pct > MAX_RISK_THRESHOLD_PCT:
        raise HTTPException(
            status_code=400,
            detail=(
                "Threshold must be between "
                f"{MIN_RISK_THRESHOLD_PCT:.0f} and {MAX_RISK_THRESHOLD_PCT:.0f}"
            ),
        )


def _build_member_risk_rows(
    db: Session,
    members: list[Member],
    days: int,
    threshold_pct: float,
) -> list[dict]:
    now = datetime.utcnow()
    since = now - timedelta(days=days)
    classes_count = (
        db.query(FitnessClass)
        .filter(FitnessClass.schedule >= since, FitnessClass.schedule <= now)
        .count()
    )
    denominator = max(classes_count, 1)
    attendance_rows = (
        db.query(Attendance.member_id, func.count(Attendance.id))
        .filter(Attendance.checked_in_at >= since, Attendance.checked_in_at <= now)
        .group_by(Attendance.member_id)
        .all()
    )
    attendance_by_member = {member_id: count for member_id, count in attendance_rows}
    booking_rows = (
        db.query(Booking.member_id, func.count(Booking.id))
        .join(FitnessClass, FitnessClass.id == Booking.class_id)
        .filter(
            Booking.status == "confirmed",
            FitnessClass.schedule >= since,
            FitnessClass.schedule <= now,
        )
        .group_by(Booking.member_id)
        .all()
    )
    booked_by_member = {member_id: count for member_id, count in booking_rows}
    rows = []
    for member in members:
        attendance_count = attendance_by_member.get(member.id, 0)
        booked_count = booked_by_member.get(member.id, 0)
        member_denominator = max(booked_count, denominator)
        attendance_rate = round((attendance_count / member_denominator) * 100.0, 2)
        at_risk = attendance_rate < threshold_pct
        rows.append(
            {
                "member_id": member.id,
                "member_no": getattr(member, "member_no", None),
                "full_name": member.full_name,
                "booked_count": booked_count,
                "attendance_count": attendance_count,
                "attendance_rate": attendance_rate,
                "at_risk": at_risk,
                "risk_window_days": days,
                "risk_threshold_pct": round(threshold_pct, 2),
                "rationale": (
                    f"Attendance {attendance_rate:.2f}% in last {days}d "
                    f"(threshold < {threshold_pct:.2f}%)"
                ),
            }
        )
    rows.sort(key=lambda r: r["attendance_rate"])
    return rows
    metrics = payload["metrics"]
    period = payload["period"]
    scope = payload["scope"]
    highlights = payload["highlights"]
    return Template(template).safe_substitute(
        report_title=escape(payload["title"]),
        generated_at=escape(payload["generated_at"]),
        period_start=escape(period["start"]),
        period_end=escape(period["end"]),
        scope_label=escape(scope["label"]),
        revenue_total=f"{metrics['revenue']['total_amount']:.2f}",
        revenue_delta_pct=f"{metrics['revenue']['change_vs_previous_week_pct']:.2f}",
        member_new=str(metrics["member_growth"]["new_members"]),
        member_base=str(metrics["member_growth"]["member_base"]),
        retention_rate=f"{metrics['member_growth']['retention_rate']:.2f}",
        classes_count=str(metrics["occupancy"]["classes_count"]),
        booked_total=str(metrics["occupancy"]["booked_total"]),
        fill_rate=f"{metrics['occupancy']['fill_rate']:.2f}",
        at_risk_count=str(metrics["at_risk"]["count"]),
        at_risk_pct=f"{metrics['at_risk']['share_of_active_members_pct']:.2f}",
        highlight_revenue=escape(highlights["revenue"]),
        highlight_member=escape(highlights["member_growth_retention"]),
        highlight_occupancy=escape(highlights["class_occupancy"]),
        highlight_risk=escape(highlights["at_risk"]),
    )


@router.get("/stats")
def get_stats(db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    total_members = db.query(Member).count()
    today = datetime.utcnow().date()
    today_start = datetime(today.year, today.month, today.day)
    today_attendance = (
        db.query(Attendance)
        .filter(Attendance.checked_in_at >= today_start)
        .count()
    )
    total_classes = db.query(FitnessClass).count()
    active_memberships = (
        db.query(Membership)
        .filter(Membership.status == "active", Membership.end_date >= datetime.utcnow())
        .count()
    )
    pending_notifications = (
        db.query(NotificationRequest).filter(NotificationRequest.status == "pending").count()
    )
    upcoming_7d_classes = (
        db.query(FitnessClass)
        .filter(
            FitnessClass.schedule >= datetime.utcnow(),
            FitnessClass.schedule <= datetime.utcnow() + timedelta(days=7),
        )
        .count()
    )
    return {
        "total_members": total_members,
        "today_attendance": today_attendance,
        "total_classes": total_classes,
        "active_memberships": active_memberships,
        "pending_notifications": pending_notifications,
        "upcoming_7d_classes": upcoming_7d_classes,
    }


@router.get("/sales")
def sales_summary(
    year: int | None = None,
    month: int | None = None,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    now = datetime.utcnow()
    y = year or now.year
    m = month or now.month
    if m < 1 or m > 12:
        raise HTTPException(status_code=400, detail="Month must be between 1 and 12")
    last = monthrange(y, m)[1]
    start = datetime(y, m, 1)
    end = datetime(y, m, last, 23, 59, 59)
    q = (
        db.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(
            Payment.status == "completed",
            Payment.created_at >= start,
            Payment.created_at <= end,
        )
        .scalar()
    )
    count = (
        db.query(Payment)
        .filter(
            Payment.status == "completed",
            Payment.created_at >= start,
            Payment.created_at <= end,
        )
        .count()
    )
    return {
        "year": y,
        "month": m,
        "completed_payment_count": count,
        "total_amount_cents": int(q or 0),
        "total_amount": (int(q or 0)) / 100.0,
    }


@router.get("/sales/trend")
def sales_trend(
    months: int = 6,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    if months < 1 or months > 24:
        raise HTTPException(status_code=400, detail="Months must be between 1 and 24")
    now = datetime.utcnow()
    y = now.year
    m = now.month
    points = []
    for _ in range(months):
        last = monthrange(y, m)[1]
        start = datetime(y, m, 1)
        end = datetime(y, m, last, 23, 59, 59)
        total = (
            db.query(func.coalesce(func.sum(Payment.amount), 0))
            .filter(
                Payment.status == "completed",
                Payment.created_at >= start,
                Payment.created_at <= end,
            )
            .scalar()
        )
        count = (
            db.query(Payment)
            .filter(
                Payment.status == "completed",
                Payment.created_at >= start,
                Payment.created_at <= end,
            )
            .count()
        )
        points.append(
            {
                "year": y,
                "month": m,
                "label": f"{y}-{m:02d}",
                "payment_count": count,
                "total_amount_cents": int(total or 0),
                "total_amount": int(total or 0) / 100.0,
            }
        )
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    points.reverse()
    return {"months": months, "points": points}


@router.get("/reports/member-growth")
def member_growth_report(
    months: int = 12,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    if months < 1 or months > 36:
        raise HTTPException(status_code=400, detail="Months must be between 1 and 36")
    now = datetime.utcnow()
    y = now.year
    m = now.month
    points = []
    for _ in range(months):
        last = monthrange(y, m)[1]
        start = datetime(y, m, 1)
        end = datetime(y, m, last, 23, 59, 59)
        new_members = (
            db.query(Member)
            .filter(Member.created_at >= start, Member.created_at <= end)
            .count()
        )
        total_members = db.query(Member).filter(Member.created_at <= end).count()
        points.append(
            {
                "year": y,
                "month": m,
                "label": f"{y}-{m:02d}",
                "new_members": new_members,
                "total_members": total_members,
            }
        )
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    points.reverse()
    return {"months": months, "points": points}


@router.get("/reports/retention")
def retention_report(
    months: int = 12,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    if months < 1 or months > 36:
        raise HTTPException(status_code=400, detail="Months must be between 1 and 36")
    now = datetime.utcnow()
    y = now.year
    m = now.month
    points = []
    for _ in range(months):
        last = monthrange(y, m)[1]
        end = datetime(y, m, last, 23, 59, 59)
        member_base = db.query(Member).filter(Member.created_at <= end).count()
        active_members = (
            db.query(func.count(func.distinct(Membership.member_id)))
            .filter(
                Membership.status == "active",
                Membership.start_date <= end,
                Membership.end_date >= end,
            )
            .scalar()
        ) or 0
        rate = (active_members / member_base * 100.0) if member_base else 0.0
        points.append(
            {
                "year": y,
                "month": m,
                "label": f"{y}-{m:02d}",
                "member_base": member_base,
                "active_members": active_members,
                "retention_rate": round(rate, 2),
            }
        )
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    points.reverse()
    return {"months": months, "points": points}


@router.get("/reports/occupancy-trend")
def occupancy_trend_report(
    months: int = 6,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    if months < 1 or months > 24:
        raise HTTPException(status_code=400, detail="Months must be between 1 and 24")
    now = datetime.utcnow()
    y = now.year
    m = now.month
    points = []
    for _ in range(months):
        last = monthrange(y, m)[1]
        start = datetime(y, m, 1)
        end = datetime(y, m, last, 23, 59, 59)
        classes = (
            db.query(FitnessClass)
            .filter(FitnessClass.schedule >= start, FitnessClass.schedule <= end)
            .all()
        )
        capacity_total = sum(c.capacity for c in classes)
        class_ids = [c.id for c in classes]
        booked_total = 0
        if class_ids:
            booked_total = (
                db.query(Booking)
                .filter(
                    Booking.class_id.in_(class_ids),
                    Booking.status == "confirmed",
                )
                .count()
            )
        fill_rate = (booked_total / capacity_total * 100.0) if capacity_total else 0.0
        points.append(
            {
                "year": y,
                "month": m,
                "label": f"{y}-{m:02d}",
                "classes_count": len(classes),
                "capacity_total": capacity_total,
                "booked_total": booked_total,
                "fill_rate": round(fill_rate, 2),
            }
        )
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    points.reverse()
    return {"months": months, "points": points}


@router.get("/reports/member-risk")
def member_risk_report(
    days: int = 30,
    threshold_pct: float = 50.0,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    _validate_member_risk_params(days, threshold_pct)
    members = db.query(Member).all()
    return _build_member_risk_rows(db=db, members=members, days=days, threshold_pct=threshold_pct)


@router.get("/reports/class-utilization")
def class_utilization_report(
    days: int = 30,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    if days < 1 or days > 180:
        raise HTTPException(status_code=400, detail="Days must be between 1 and 180")
    start = datetime.utcnow() - timedelta(days=days)
    classes = (
        db.query(FitnessClass)
        .filter(FitnessClass.schedule >= start)
        .order_by(FitnessClass.schedule.desc())
        .all()
    )
    rows = []
    total_fill = 0.0
    for c in classes:
        booked = (
            db.query(Booking)
            .filter(Booking.class_id == c.id, Booking.status != "cancelled")
            .count()
        )
        fill = (booked / c.capacity * 100.0) if c.capacity else 0.0
        total_fill += fill
        rows.append(
            {
                "class_id": c.id,
                "name": c.name,
                "instructor": c.instructor,
                "schedule": c.schedule,
                "capacity": c.capacity,
                "booked_count": booked,
                "fill_rate": round(fill, 2),
            }
        )
    avg_fill = round(total_fill / len(rows), 2) if rows else 0.0
    return {
        "days": days,
        "average_fill_rate": avg_fill,
        "classes_count": len(rows),
        "rows": rows,
    }


@router.get("/reports/premium-overview")
def premium_overview_report(
    months: int = 6,
    risk_days: int = 60,
    risk_threshold_pct: float = 50.0,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    if months < 3 or months > 24:
        raise HTTPException(status_code=400, detail="Months must be between 3 and 24")
    _validate_member_risk_params(risk_days, risk_threshold_pct)

    mrr = sales_trend(months=months, db=db, _={})
    retention = retention_report(months=months, db=db, _={})
    occupancy = occupancy_trend_report(months=months, db=db, _={})
    risk_rows = _build_member_risk_rows(
        db=db,
        members=db.query(Member).all(),
        days=risk_days,
        threshold_pct=risk_threshold_pct,
    )

    latest_mrr = mrr["points"][-1] if mrr["points"] else None
    previous_mrr = mrr["points"][-2] if len(mrr["points"]) > 1 else None
    latest_mrr_total = float((latest_mrr or {}).get("total_amount") or 0.0)
    previous_mrr_total = float((previous_mrr or {}).get("total_amount") or 0.0)
    mrr_delta_pct = 0.0
    if previous_mrr_total > 0:
        mrr_delta_pct = ((latest_mrr_total - previous_mrr_total) / previous_mrr_total) * 100.0

    latest_retention = retention["points"][-1] if retention["points"] else None
    previous_retention = retention["points"][-2] if len(retention["points"]) > 1 else None
    latest_retention_rate = float((latest_retention or {}).get("retention_rate") or 0.0)
    previous_retention_rate = float((previous_retention or {}).get("retention_rate") or 0.0)
    retention_delta_pct = latest_retention_rate - previous_retention_rate

    latest_occupancy = occupancy["points"][-1] if occupancy["points"] else None
    previous_occupancy = occupancy["points"][-2] if len(occupancy["points"]) > 1 else None
    latest_fill_rate = float((latest_occupancy or {}).get("fill_rate") or 0.0)
    previous_fill_rate = float((previous_occupancy or {}).get("fill_rate") or 0.0)
    occupancy_delta_pct = latest_fill_rate - previous_fill_rate

    active_members = (
        db.query(func.count(func.distinct(Membership.member_id)))
        .filter(
            Membership.status == "active",
            Membership.start_date <= datetime.utcnow(),
            Membership.end_date >= datetime.utcnow(),
        )
        .scalar()
    ) or 0
    at_risk_count = sum(1 for row in risk_rows if row["at_risk"])
    at_risk_share = (at_risk_count / active_members * 100.0) if active_members else 0.0
    top_at_risk = [
        {
            "member_id": row["member_id"],
            "member_no": row.get("member_no"),
            "full_name": row["full_name"],
            "attendance_rate": row["attendance_rate"],
            "booked_count": row["booked_count"],
            "attendance_count": row["attendance_count"],
            "rationale": row["rationale"],
        }
        for row in risk_rows
        if row["at_risk"]
    ][:5]

    return {
        "months": months,
        "kpis": {
            "mrr": {
                "label": "MRR",
                "value": round(latest_mrr_total, 2),
                "value_cents": int((latest_mrr or {}).get("total_amount_cents") or 0),
                "delta_pct": round(mrr_delta_pct, 2),
                "status": "up" if mrr_delta_pct >= 0 else "down",
            },
            "retention_proxy": {
                "label": "Retention proxy",
                "value": round(latest_retention_rate, 2),
                "delta_pct": round(retention_delta_pct, 2),
                "status": "up" if retention_delta_pct >= 0 else "down",
                "active_members": int((latest_retention or {}).get("active_members") or 0),
                "member_base": int((latest_retention or {}).get("member_base") or 0),
            },
            "occupancy": {
                "label": "Occupancy",
                "value": round(latest_fill_rate, 2),
                "delta_pct": round(occupancy_delta_pct, 2),
                "status": "up" if occupancy_delta_pct >= 0 else "down",
                "capacity_total": int((latest_occupancy or {}).get("capacity_total") or 0),
                "booked_total": int((latest_occupancy or {}).get("booked_total") or 0),
            },
            "at_risk": {
                "label": "At-risk members",
                "count": at_risk_count,
                "share_of_active_members_pct": round(at_risk_share, 2),
                "status": "alert" if at_risk_count > 0 else "stable",
                "risk_window_days": risk_days,
                "risk_threshold_pct": round(risk_threshold_pct, 2),
            },
        },
        "trends": {
            "mrr": mrr["points"],
            "retention_proxy": retention["points"],
            "occupancy": occupancy["points"],
        },
        "at_risk_summary": {
            "count": at_risk_count,
            "risk_window_days": risk_days,
            "risk_threshold_pct": round(risk_threshold_pct, 2),
            "share_of_active_members_pct": round(at_risk_share, 2),
            "top_members": top_at_risk,
        },
    }


@router.get("/reports/weekly-performance")
def weekly_performance_report(
    center_id: int | None = None,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    now = datetime.utcnow()
    week_end = datetime(now.year, now.month, now.day, 23, 59, 59)
    week_start = week_end - timedelta(days=6)
    prev_week_end = week_start - timedelta(seconds=1)
    prev_week_start = prev_week_end - timedelta(days=6)

    class_filter = []
    payment_filter = []
    membership_filter = []
    member_filter = []
    scope_label = "Global Admin"

    if center_id is not None:
        center = db.query(Center).filter(Center.id == center_id).first()
        if not center:
            raise HTTPException(status_code=404, detail="Center not found")
        scope_label = f"Center #{center.id} - {center.name}"
        class_filter.append(FitnessClass.center_id == center_id)
        payment_filter.append(Payment.center_id == center_id)
        membership_filter.extend(
            [
                CenterMembership.center_id == center_id,
                CenterMembership.status == "active",
            ]
        )
        member_filter.append(
            Member.id.in_(
                db.query(CenterMembership.member_id).filter(*membership_filter).subquery()
            )
        )

    current_revenue_q = db.query(func.coalesce(func.sum(Payment.amount), 0)).filter(
        Payment.status == "completed",
        Payment.created_at >= week_start,
        Payment.created_at <= week_end,
        *payment_filter,
    )
    previous_revenue_q = db.query(func.coalesce(func.sum(Payment.amount), 0)).filter(
        Payment.status == "completed",
        Payment.created_at >= prev_week_start,
        Payment.created_at <= prev_week_end,
        *payment_filter,
    )
    current_revenue_cents = int(current_revenue_q.scalar() or 0)
    previous_revenue_cents = int(previous_revenue_q.scalar() or 0)
    revenue_delta_pct = 0.0
    if previous_revenue_cents > 0:
        revenue_delta_pct = (
            (current_revenue_cents - previous_revenue_cents) / previous_revenue_cents
        ) * 100.0

    new_members = (
        db.query(Member)
        .filter(Member.created_at >= week_start, Member.created_at <= week_end, *member_filter)
        .count()
    )
    member_base = db.query(Member).filter(Member.created_at <= week_end, *member_filter).count()

    active_members_q = db.query(func.count(func.distinct(Membership.member_id))).filter(
        Membership.status == "active",
        Membership.start_date <= week_end,
        Membership.end_date >= week_end,
    )
    if center_id is not None:
        active_members_q = active_members_q.filter(
            Membership.member_id.in_(
                db.query(CenterMembership.member_id).filter(*membership_filter).subquery()
            )
        )
    active_members = int(active_members_q.scalar() or 0)
    retention_rate = (active_members / member_base * 100.0) if member_base else 0.0

    weekly_classes = (
        db.query(FitnessClass)
        .filter(
            FitnessClass.schedule >= week_start,
            FitnessClass.schedule <= week_end,
            *class_filter,
        )
        .all()
    )
    class_ids = [c.id for c in weekly_classes]
    capacity_total = sum(c.capacity for c in weekly_classes)
    booked_total = 0
    if class_ids:
        booked_total = (
            db.query(Booking)
            .filter(Booking.class_id.in_(class_ids), Booking.status == "confirmed")
            .count()
        )
    fill_rate = (booked_total / capacity_total * 100.0) if capacity_total else 0.0

    risk_days = 60
    since = now - timedelta(days=risk_days)
    classes_count_window = (
        db.query(FitnessClass)
        .filter(
            FitnessClass.schedule >= since,
            FitnessClass.schedule <= now,
            *class_filter,
        )
        .count()
    )
    denominator = max(classes_count_window, 1)
    members_q = db.query(Member).filter(*member_filter)
    members = members_q.all()
    attendance_rows = (
        db.query(Attendance.member_id, func.count(Attendance.id))
        .filter(Attendance.checked_in_at >= since)
        .group_by(Attendance.member_id)
        .all()
    )
    attendance_by_member = {member_id: count for member_id, count in attendance_rows}
    booking_rows = (
        db.query(Booking.member_id, func.count(Booking.id))
        .join(FitnessClass, FitnessClass.id == Booking.class_id)
        .filter(
            Booking.status == "confirmed",
            FitnessClass.schedule >= since,
            FitnessClass.schedule <= now,
            *class_filter,
        )
        .group_by(Booking.member_id)
        .all()
    )
    booked_by_member = {member_id: count for member_id, count in booking_rows}
    at_risk_count = 0
    for member in members:
        attendance_count = attendance_by_member.get(member.id, 0)
        booked_count = booked_by_member.get(member.id, 0)
        member_denominator = max(booked_count, denominator)
        attendance_rate = (attendance_count / member_denominator) * 100.0
        if attendance_rate <= 50.0:
            at_risk_count += 1
    at_risk_pct = (at_risk_count / active_members * 100.0) if active_members else 0.0

    payload = {
        "title": "Weekly Performance Report",
        "generated_at": now.isoformat(),
        "period": {
            "start": week_start.date().isoformat(),
            "end": week_end.date().isoformat(),
        },
        "scope": {
            "center_id": center_id,
            "label": scope_label,
        },
        "metrics": {
            "revenue": {
                "total_amount_cents": current_revenue_cents,
                "total_amount": current_revenue_cents / 100.0,
                "change_vs_previous_week_pct": round(revenue_delta_pct, 2),
            },
            "member_growth": {
                "new_members": new_members,
                "member_base": member_base,
                "active_members": active_members,
                "retention_rate": round(retention_rate, 2),
            },
            "occupancy": {
                "classes_count": len(weekly_classes),
                "capacity_total": capacity_total,
                "booked_total": booked_total,
                "fill_rate": round(fill_rate, 2),
            },
            "at_risk": {
                "count": at_risk_count,
                "risk_window_days": risk_days,
                "share_of_active_members_pct": round(at_risk_pct, 2),
            },
        },
    }
    payload["highlights"] = {
        "revenue": (
            f"Revenue reached {payload['metrics']['revenue']['total_amount']:.2f} "
            f"({payload['metrics']['revenue']['change_vs_previous_week_pct']:.2f}% vs last week)."
        ),
        "member_growth_retention": (
            f"Added {new_members} members this week with "
            f"{payload['metrics']['member_growth']['retention_rate']:.2f}% retention."
        ),
        "class_occupancy": (
            f"{len(weekly_classes)} classes delivered at "
            f"{payload['metrics']['occupancy']['fill_rate']:.2f}% average fill."
        ),
        "at_risk": (
            f"{at_risk_count} members are at risk based on the last {risk_days} days."
        ),
    }
    payload["html"] = _render_weekly_report_html(payload)
    return payload


@router.post("/notifications/membership-reminders/run")
def run_membership_reminders(
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    result = queue_membership_expiry_reminders(db)
    return {"status": "queued", **result}


@router.post("/notifications/dispatch/run")
def run_notification_dispatch(
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    result = process_pending_notifications(db)
    return {"status": "processed", **result}


@router.get("/attendances/recent")
def get_recent_attendances(db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    attendances = (
        db.query(Attendance).order_by(Attendance.checked_in_at.desc()).limit(20).all()
    )
    result = []
    for a in attendances:
        member = db.query(Member).filter(Member.id == a.member_id).first()
        fitness_class = (
            db.query(FitnessClass).filter(FitnessClass.id == a.class_id).first()
        )
        result.append(
            {
                "member_name": member.full_name if member else "Unknown",
                "class_name": fitness_class.name if fitness_class else "Unknown",
                "checked_in_at": a.checked_in_at,
                "status": a.status,
            }
        )
    return result


@router.get("/members")
def get_members(
    risk_days: int = 30,
    risk_threshold_pct: float = 50.0,
    include_retention_risk: bool = True,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    _validate_member_risk_params(risk_days, risk_threshold_pct)
    members = db.query(Member).all()
    risk_by_member_id = {}
    if include_retention_risk:
        risk_rows = _build_member_risk_rows(
            db=db,
            members=members,
            days=risk_days,
            threshold_pct=risk_threshold_pct,
        )
        risk_by_member_id = {row["member_id"]: row for row in risk_rows}
    return [
        {
            "id": m.id,
            "full_name": m.full_name,
            "email": m.email,
            "phone": m.phone,
            "birth_date": getattr(m, "birth_date", None),
            "member_no": getattr(m, "member_no", None),
            "member_level": getattr(m, "member_level", "starter"),
            "is_active": m.is_active,
            "role": getattr(m, "role", "member"),
            "created_at": m.created_at,
            "at_risk": risk_by_member_id.get(m.id, {}).get("at_risk"),
            "attendance_rate": risk_by_member_id.get(m.id, {}).get("attendance_rate"),
            "risk_reason": risk_by_member_id.get(m.id, {}).get("rationale"),
            "retention_risk": (
                {
                    "at_risk": risk_by_member_id.get(m.id, {}).get("at_risk"),
                    "attendance_rate": risk_by_member_id.get(m.id, {}).get(
                        "attendance_rate"
                    ),
                    "attendance_count": risk_by_member_id.get(m.id, {}).get(
                        "attendance_count"
                    ),
                    "booked_count": risk_by_member_id.get(m.id, {}).get("booked_count"),
                    "risk_window_days": risk_by_member_id.get(m.id, {}).get(
                        "risk_window_days"
                    ),
                    "risk_threshold_pct": risk_by_member_id.get(m.id, {}).get(
                        "risk_threshold_pct"
                    ),
                    "rationale": risk_by_member_id.get(m.id, {}).get("rationale"),
                }
                if include_retention_risk
                else None
            ),
        }
        for m in members
    ]


@router.get("/payments")
def list_payments(
    limit: int = 100,
    format: str | None = None,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    rows = (
        db.query(Payment).order_by(Payment.created_at.desc()).limit(min(limit, 500)).all()
    )
    data = []
    for p in rows:
        metadata = build_payment_metadata(
            method=getattr(p, "payment_method", "card"),
            status=p.status,
            external_ref=getattr(p, "external_ref", None),
        )
        data.append(
            {
            "id": p.id,
            "member_id": p.member_id,
            "membership_id": p.membership_id,
            "amount": p.amount / 100.0,
            "amount_cents": p.amount,
            "currency": p.currency,
            "status": p.status,
            "source": getattr(p, "source", "online"),
            "payment_method": getattr(p, "payment_method", "card"),
            "external_ref": getattr(p, "external_ref", None),
            "provider": metadata["provider"],
            "provider_reference": metadata["provider_reference"],
            "fee_hint_bps": metadata["fee_hint_bps"],
            "settlement_state": metadata["settlement_state"],
            "center_id": getattr(p, "center_id", None),
            "memo": getattr(p, "memo", None),
            "created_at": p.created_at,
            }
        )
    if (format or "").strip().lower() != "csv":
        return data
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=[
            "id",
            "member_id",
            "membership_id",
            "amount",
            "amount_cents",
            "currency",
            "status",
            "source",
            "payment_method",
            "provider",
            "external_ref",
            "provider_reference",
            "fee_hint_bps",
            "settlement_state",
            "center_id",
            "memo",
            "created_at",
        ],
    )
    writer.writeheader()
    for row in data:
        csv_row = row.copy()
        csv_row["created_at"] = (
            csv_row["created_at"].isoformat() if csv_row.get("created_at") else ""
        )
        writer.writerow(csv_row)
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="payments_export.csv"'},
    )


@router.get("/classes")
def list_classes_admin(db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    classes = db.query(FitnessClass).order_by(FitnessClass.schedule.asc()).all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "instructor": c.instructor,
            "schedule": c.schedule,
            "capacity": c.capacity,
            "current_count": c.current_count,
            "center_id": getattr(c, "center_id", None),
            "level_required": getattr(c, "level_required", "starter"),
        }
        for c in classes
    ]


class InstructorCreate(BaseModel):
    display_name: str = Field(..., min_length=1)
    hourly_rate_cents: int = Field(50_000, ge=0)
    pay_per_class_cents: int = Field(80_000, ge=0)
    email: str | None = None
    avatar_url: str | None = None
    bio: str | None = None
    specialties: str | None = None
    notes: str | None = None


class InstructorUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1)
    hourly_rate_cents: int | None = Field(default=None, ge=0)
    pay_per_class_cents: int | None = Field(default=None, ge=0)
    email: str | None = None
    avatar_url: str | None = None
    bio: str | None = None
    specialties: str | None = None
    notes: str | None = None


class ClassCreateAdmin(BaseModel):
    name: str = Field(..., min_length=1)
    instructor: str = Field(..., min_length=1)
    schedule: datetime
    capacity: int = Field(default=20, ge=1, le=500)
    center_id: int | None = None
    level_required: str = Field(default="starter", pattern="^(starter|core|elite|vip)$")


class ClassUpdateAdmin(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    instructor: str | None = Field(default=None, min_length=1)
    schedule: datetime | None = None
    capacity: int | None = Field(default=None, ge=1, le=500)
    center_id: int | None = None
    level_required: str | None = Field(default=None, pattern="^(starter|core|elite|vip)$")


@router.get("/instructors")
def list_instructors(db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    rows = db.query(InstructorProfile).order_by(InstructorProfile.display_name).all()
    return [
        {
            "id": r.id,
            "display_name": r.display_name,
            "hourly_rate_cents": r.hourly_rate_cents,
            "pay_per_class_cents": r.pay_per_class_cents,
            "email": r.email,
            "avatar_url": getattr(r, "avatar_url", None),
            "bio": getattr(r, "bio", None),
            "specialties": getattr(r, "specialties", None),
            "notes": r.notes,
        }
        for r in rows
    ]


@router.post("/instructors", status_code=201)
def create_instructor(
    body: InstructorCreate,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    exists = (
        db.query(InstructorProfile)
        .filter(InstructorProfile.display_name == body.display_name)
        .first()
    )
    if exists:
        raise HTTPException(status_code=400, detail="Instructor name already exists")
    row = InstructorProfile(
        display_name=body.display_name.strip(),
        hourly_rate_cents=body.hourly_rate_cents,
        pay_per_class_cents=body.pay_per_class_cents,
        email=body.email,
        avatar_url=body.avatar_url,
        bio=body.bio,
        specialties=body.specialties,
        notes=body.notes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "display_name": row.display_name}


@router.put("/instructors/{instructor_id}")
def update_instructor(
    instructor_id: int,
    body: InstructorUpdate,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    row = db.query(InstructorProfile).filter(InstructorProfile.id == instructor_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Instructor not found")
    if body.display_name is not None:
        old_name = row.display_name
        dup = (
            db.query(InstructorProfile)
            .filter(
                InstructorProfile.display_name == body.display_name.strip(),
                InstructorProfile.id != instructor_id,
            )
            .first()
        )
        if dup:
            raise HTTPException(status_code=400, detail="Instructor name already exists")
        row.display_name = body.display_name.strip()
        (
            db.query(FitnessClass)
            .filter(FitnessClass.instructor == old_name)
            .update({"instructor": row.display_name}, synchronize_session=False)
        )
    if body.hourly_rate_cents is not None:
        row.hourly_rate_cents = body.hourly_rate_cents
    if body.pay_per_class_cents is not None:
        row.pay_per_class_cents = body.pay_per_class_cents
    if body.email is not None:
        row.email = body.email
    if body.avatar_url is not None:
        row.avatar_url = body.avatar_url
    if body.bio is not None:
        row.bio = body.bio
    if body.specialties is not None:
        row.specialties = body.specialties
    if body.notes is not None:
        row.notes = body.notes
    db.commit()
    db.refresh(row)
    return {"id": row.id, "display_name": row.display_name}


@router.delete("/instructors/{instructor_id}")
def delete_instructor(
    instructor_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    row = db.query(InstructorProfile).filter(InstructorProfile.id == instructor_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Instructor not found")
    has_upcoming = (
        db.query(FitnessClass)
        .filter(
            FitnessClass.instructor == row.display_name,
            FitnessClass.schedule >= datetime.utcnow(),
        )
        .first()
    )
    if has_upcoming:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete instructor with upcoming classes",
        )
    db.delete(row)
    db.commit()
    return {"deleted": True}


@router.post("/classes", status_code=201)
def create_class_admin(
    body: ClassCreateAdmin,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    if body.schedule <= datetime.utcnow():
        raise HTTPException(status_code=400, detail="Class schedule must be in the future")
    has_instructor_profiles = db.query(InstructorProfile).count() > 0
    if has_instructor_profiles:
        profile = (
            db.query(InstructorProfile)
            .filter(InstructorProfile.display_name == body.instructor.strip())
            .first()
        )
        if not profile:
            raise HTTPException(
                status_code=400,
                detail="Instructor must exist in instructor profiles",
            )
    row = FitnessClass(
        name=body.name.strip(),
        instructor=body.instructor.strip(),
        schedule=body.schedule,
        capacity=body.capacity,
        center_id=body.center_id,
        level_required=body.level_required,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id}


@router.put("/classes/{class_id}")
def update_class_admin(
    class_id: int,
    body: ClassUpdateAdmin,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    row = db.query(FitnessClass).filter(FitnessClass.id == class_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Class not found")
    if body.name is not None:
        row.name = body.name.strip()
    if body.instructor is not None:
        row.instructor = body.instructor.strip()
    if body.schedule is not None:
        if body.schedule <= datetime.utcnow():
            raise HTTPException(
                status_code=400, detail="Class schedule must be in the future"
            )
        row.schedule = body.schedule
    if body.instructor is not None:
        has_instructor_profiles = db.query(InstructorProfile).count() > 0
        if has_instructor_profiles:
            profile = (
                db.query(InstructorProfile)
                .filter(InstructorProfile.display_name == body.instructor.strip())
                .first()
            )
            if not profile:
                raise HTTPException(
                    status_code=400,
                    detail="Instructor must exist in instructor profiles",
                )
    if body.capacity is not None:
        if body.capacity < row.current_count:
            raise HTTPException(
                status_code=400,
                detail="Capacity cannot be lower than current bookings",
            )
        previous_capacity = row.capacity
        previous_count = row.current_count
        row.capacity = body.capacity
        row.current_count = min(row.current_count, row.capacity)
        previous_open_seats = max(0, previous_capacity - previous_count)
        current_open_seats = max(0, row.capacity - row.current_count)
        newly_available_seats = max(0, current_open_seats - previous_open_seats)
        if newly_available_seats > 0:
            promote_waitlist_for_available_seats(
                db=db,
                fitness_class=row,
                max_promotions=newly_available_seats,
            )
    if body.center_id is not None:
        row.center_id = body.center_id
    if body.level_required is not None:
        row.level_required = body.level_required
    db.commit()
    db.refresh(row)
    return {"id": row.id, "updated": True}


@router.delete("/classes/{class_id}")
def delete_class_admin(
    class_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    row = db.query(FitnessClass).filter(FitnessClass.id == class_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Class not found")
    db.query(Booking).filter(Booking.class_id == class_id).delete()
    db.delete(row)
    db.commit()
    return {"deleted": True}


@router.get("/instructors/{instructor_id}/payroll")
def instructor_payroll(
    instructor_id: int,
    year: int,
    month: int,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    prof = db.query(InstructorProfile).filter(InstructorProfile.id == instructor_id).first()
    if not prof:
        raise HTTPException(status_code=404, detail="Instructor not found")
    last = monthrange(year, month)[1]
    start = datetime(year, month, 1)
    end = datetime(year, month, last, 23, 59, 59)
    cnt = (
        db.query(FitnessClass)
        .filter(
            FitnessClass.instructor == prof.display_name,
            FitnessClass.schedule >= start,
            FitnessClass.schedule <= end,
        )
        .count()
    )
    gross = cnt * prof.pay_per_class_cents
    hours_equivalent = cnt * 1.5
    hourly_based = int(hours_equivalent * prof.hourly_rate_cents)
    recommended = max(gross, hourly_based)
    return {
        "instructor_id": prof.id,
        "display_name": prof.display_name,
        "year": year,
        "month": month,
        "classes_scheduled": cnt,
        "pay_per_class_cents": prof.pay_per_class_cents,
        "hourly_rate_cents": prof.hourly_rate_cents,
        "flat_total_cents": gross,
        "hourly_based_total_cents": hourly_based,
        "recommended_monthly_pay_cents": recommended,
        "recommended_monthly_pay": recommended / 100.0,
    }


class NotificationCreate(BaseModel):
    member_id: int | None = None
    topic: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    channel: str = Field(default="email", pattern="^(email|sms|inapp)$")


class NotificationStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(pending|sent|failed)$")


class MemberAdminUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1)
    phone: str | None = None
    birth_date: date | None = None
    member_no: str | None = None
    member_level: str | None = Field(default=None, pattern="^(starter|core|elite|vip)$")
    is_active: bool | None = None
    role: str | None = Field(default=None, pattern="^(member|admin)$")


@router.get("/notifications")
def list_notifications(
    limit: int = 50,
    status: str | None = None,
    channel: str | None = None,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    q = db.query(NotificationRequest)
    if status in {"pending", "sent", "failed"}:
        q = q.filter(NotificationRequest.status == status)
    if channel in {"email", "sms", "inapp"}:
        q = q.filter(NotificationRequest.channel == channel)
    rows = q.order_by(NotificationRequest.created_at.desc()).limit(min(limit, 200)).all()
    return [
        {
            "id": r.id,
            "member_id": r.member_id,
            "topic": r.topic,
            "message": r.message,
            "channel": getattr(r, "channel", "email"),
            "status": r.status,
            "retry_count": getattr(r, "retry_count", 0),
            "max_retries": getattr(r, "max_retries", 3),
            "next_attempt_at": getattr(r, "next_attempt_at", None),
            "last_error": getattr(r, "last_error", None),
            "sent_at": getattr(r, "sent_at", None),
            "created_at": r.created_at,
        }
        for r in rows
    ]


@router.get("/notifications/summary")
def notifications_summary(
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    queued = db.query(NotificationRequest).filter(NotificationRequest.status == "pending").count()
    sent = db.query(NotificationRequest).filter(NotificationRequest.status == "sent").count()
    failed = db.query(NotificationRequest).filter(NotificationRequest.status == "failed").count()
    retrying = (
        db.query(NotificationRequest)
        .filter(
            NotificationRequest.status == "pending",
            NotificationRequest.retry_count > 0,
        )
        .count()
    )
    by_channel_rows = (
        db.query(NotificationRequest.channel, func.count(NotificationRequest.id))
        .group_by(NotificationRequest.channel)
        .all()
    )
    by_channel = {channel or "email": count for channel, count in by_channel_rows}
    return {
        "queued": queued,
        "sent": sent,
        "failed": failed,
        "retrying": retrying,
        "by_channel": {
            "email": by_channel.get("email", 0),
            "sms": by_channel.get("sms", 0),
            "inapp": by_channel.get("inapp", 0),
        },
    }


@router.post("/notifications", status_code=201)
def create_notification(
    body: NotificationCreate,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    row = NotificationRequest(
        member_id=body.member_id,
        topic=body.topic.strip(),
        message=body.message.strip(),
        channel=body.channel,
        status="pending",
        retry_count=0,
        max_retries=3,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "status": row.status}


@router.patch("/notifications/{notification_id}/status")
def update_notification_status(
    notification_id: int,
    body: NotificationStatusUpdate,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    row = (
        db.query(NotificationRequest)
        .filter(NotificationRequest.id == notification_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Notification not found")
    row.status = body.status
    db.commit()
    db.refresh(row)
    return {"id": row.id, "status": row.status}


@router.post("/notifications/{notification_id}/retry")
def retry_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    row = (
        db.query(NotificationRequest)
        .filter(NotificationRequest.id == notification_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Notification not found")
    row.status = "pending"
    row.next_attempt_at = None
    row.last_error = None
    db.commit()
    db.refresh(row)
    return {"id": row.id, "status": row.status}


@router.get("/notifications/{notification_id}/attempts")
def notification_attempts(
    notification_id: int,
    limit: int = 30,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    rows = (
        db.query(NotificationDeliveryAttempt)
        .filter(NotificationDeliveryAttempt.notification_id == notification_id)
        .order_by(NotificationDeliveryAttempt.attempted_at.desc())
        .limit(min(max(limit, 1), 200))
        .all()
    )
    return [
        {
            "id": r.id,
            "notification_id": r.notification_id,
            "channel": r.channel,
            "status": r.status,
            "provider_message_id": r.provider_message_id,
            "error_message": r.error_message,
            "attempted_at": r.attempted_at,
        }
        for r in rows
    ]


@router.put("/members/{member_id}")
def update_member_admin(
    member_id: int,
    body: MemberAdminUpdate,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin),
):
    row = db.query(Member).filter(Member.id == member_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Member not found")
    if body.full_name is not None:
        row.full_name = body.full_name.strip()
    if body.phone is not None:
        row.phone = body.phone.strip()
    if body.birth_date is not None:
        row.birth_date = body.birth_date
    if body.member_level is not None:
        row.member_level = body.member_level
    if body.is_active is not None:
        row.is_active = body.is_active
    if body.role is not None:
        row.role = body.role
    if body.member_no is not None:
        normalized = body.member_no.strip()
        if normalized:
            dup = (
                db.query(Member)
                .filter(Member.member_no == normalized, Member.id != member_id)
                .first()
            )
            if dup:
                raise HTTPException(status_code=400, detail="Member number already exists")
            row.member_no = normalized
        else:
            row.member_no = None
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "full_name": row.full_name,
        "phone": row.phone,
        "birth_date": getattr(row, "birth_date", None),
        "member_no": row.member_no,
        "member_level": getattr(row, "member_level", "starter"),
        "is_active": row.is_active,
        "role": row.role,
    }
