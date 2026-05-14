"use client";

import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

import { ActionButton } from "@/components/atoms/action-button";
import { Badge } from "@/components/atoms/badge";
import { classSlots, waitlistEntries } from "@/lib/mock-data";
import { apiFetch } from "@/lib/api";
import type { ClassSlot, LiveClassSlot } from "@/types/domain";

type QuickReserveModalProps = {
  open: boolean;
  onClose: () => void;
};

export function QuickReserveModal({
  open,
  onClose
}: QuickReserveModalProps): JSX.Element {
  const [selectedClassId, setSelectedClassId] = useState<string>(classSlots[0]?.id ?? "");
  const [step, setStep] = useState<1 | 2>(1);
  const [memberId, setMemberId] = useState<string>("");
  const [slots, setSlots] = useState<ClassSlot[]>(classSlots);
  const [waitlistLive, setWaitlistLive] = useState<
    Array<{ booking_id: number; member_name: string; member_no?: string | null }>
  >([]);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [flash, setFlash] = useState<string>("");

  useEffect(() => {
    if (typeof window === "undefined") return;
    const storedMemberId = window.localStorage.getItem("member_id") ?? "";
    setMemberId(storedMemberId);
  }, []);

  useEffect(() => {
    if (!open) return;
    let mounted = true;
    apiFetch<LiveClassSlot[]>("/classes")
      .then((rows) => {
        if (!mounted) return;
        const mapped: ClassSlot[] = rows.map((row) => ({
          id: String(row.id),
          title: row.title ?? row.name ?? "Class",
          coach: row.coach ?? row.instructor ?? "Coach",
          startsAt: row.startsAt ?? row.schedule,
          capacity: row.capacity,
          booked: row.booked ?? row.current_count ?? 0,
          waitlist: row.waitlist ?? 0
        }));
        if (mapped.length > 0) {
          setSlots(mapped);
          if (!mapped.find((slot) => slot.id === selectedClassId)) {
            setSelectedClassId(mapped[0].id);
          }
        }
      })
      .catch(() => {
        setSlots(classSlots);
      });
    return () => {
      mounted = false;
    };
  }, [open, selectedClassId]);

  const selectedClass: ClassSlot | undefined = useMemo(
    () => slots.find((slot) => slot.id === selectedClassId),
    [selectedClassId, slots]
  );

  const full = selectedClass ? selectedClass.booked >= selectedClass.capacity : false;

  useEffect(() => {
    if (!open || !selectedClassId || !full) {
      setWaitlistLive([]);
      return;
    }
    apiFetch<Array<{ booking_id: number; member_name: string; member_no?: string | null }>>(
      `/classes/${selectedClassId}/waitlist`
    )
      .then((rows) => setWaitlistLive(rows))
      .catch(() => setWaitlistLive([]));
  }, [open, selectedClassId, full]);

  async function handleConfirm(): Promise<void> {
    if (!memberId) {
      setFlash("Login required to reserve.");
      return;
    }
    if (!selectedClassId) {
      setFlash("Select class to continue.");
      return;
    }
    setSubmitting(true);
    setFlash("");
    try {
      const result = await apiFetch<{
        message: string;
        waitlisted?: boolean;
        waitlist_position?: number;
      }>(`/classes/${selectedClassId}/book?member_id=${memberId}`, { method: "POST" });
      if (result.waitlisted) {
        setFlash(`${result.message} (#${result.waitlist_position ?? "-"})`);
      } else {
        setFlash(result.message);
      }
      setStep(2);
    } catch (error) {
      setFlash(error instanceof Error ? error.message : "Reservation failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AnimatePresence>
      {open ? (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          onClick={onClose}
        >
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 20, opacity: 0 }}
            className="w-full max-w-xl rounded-xl2 border border-border bg-panel p-5 shadow-soft"
            onClick={(event) => event.stopPropagation()}
          >
            <header className="mb-4">
              <p className="text-xs uppercase tracking-[0.2em] text-silver">
                Quick-Reserve
              </p>
              <h3 className="mt-2 text-xl font-semibold">
                Two taps to lock your class
              </h3>
              <p className="text-sm text-muted">
                Mindbody-style waitlist included. Step {step} / 2.
              </p>
            </header>

            <div className="space-y-3">
              {slots.map((slot) => {
                const isSelected = slot.id === selectedClassId;
                const isFull = slot.booked >= slot.capacity;
                return (
                  <button
                    key={slot.id}
                    type="button"
                    className={`w-full rounded-xl border p-3 text-left transition ${
                      isSelected
                        ? "border-accent/70 bg-accent/10"
                        : "border-border bg-panelElevated hover:border-silver/45"
                    }`}
                    onClick={() => {
                      setSelectedClassId(slot.id);
                      setStep(2);
                    }}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="font-medium">{slot.title}</p>
                        <p className="text-xs text-muted">
                          {slot.coach} · {new Date(slot.startsAt).toLocaleString()}
                        </p>
                      </div>
                      {isFull ? (
                        <Badge tone="danger">Full · Waitlist {slot.waitlist}</Badge>
                      ) : (
                        <Badge tone="accent">
                          {slot.booked}/{slot.capacity}
                        </Badge>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>

            <div className="mt-4 rounded-xl border border-border bg-panelElevated p-4 text-sm">
              <p className="font-medium">
                {full ? "Class is full. Join waitlist?" : "Class spot available. Confirm now?"}
              </p>
              <p className="mt-1 text-xs text-muted">
                {selectedClass
                  ? `${selectedClass.title} · ${new Date(selectedClass.startsAt).toLocaleString()}`
                  : "Select class to continue"}
              </p>

              {full ? (
                <div className="mt-3">
                  <p className="mb-2 text-xs text-muted">Current waitlist snapshot</p>
                  <ul className="space-y-1 text-xs text-silver">
                    {(waitlistLive.length > 0 ? waitlistLive : waitlistEntries).map((entry, index) => (
                      <li key={entry.booking_id ?? entry.id}>
                        {"member_name" in entry
                          ? `${entry.member_no ?? "—"} · ${entry.member_name} · waiting`
                          : `${entry.memberNo} · ${entry.memberName} · ${entry.status}`}
                        {waitlistLive.length > 0 ? ` · #${index + 1}` : ""}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </div>
            {flash ? <p className="mt-3 text-xs text-accent">{flash}</p> : null}

            <div className="mt-5 flex items-center justify-end gap-2">
              <ActionButton tone="ghost" onClick={onClose}>
                Close
              </ActionButton>
              <ActionButton
                tone={full ? "danger" : "primary"}
                onClick={handleConfirm}
                disabled={submitting}
              >
                {full ? "Join Waitlist" : "Confirm Reservation"}
              </ActionButton>
            </div>
          </motion.div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}
