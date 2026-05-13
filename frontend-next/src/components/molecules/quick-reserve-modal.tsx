"use client";

import { useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

import { ActionButton } from "@/components/atoms/action-button";
import { Badge } from "@/components/atoms/badge";
import { classSlots, waitlistEntries } from "@/lib/mock-data";
import type { ClassSlot } from "@/types/domain";

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

  const selectedClass: ClassSlot | undefined = useMemo(
    () => classSlots.find((slot) => slot.id === selectedClassId),
    [selectedClassId]
  );

  const full = selectedClass ? selectedClass.booked >= selectedClass.capacity : false;

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
              {classSlots.map((slot) => {
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
                    {waitlistEntries.map((entry) => (
                      <li key={entry.id}>
                        {entry.memberNo} · {entry.memberName} · {entry.status}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </div>

            <div className="mt-5 flex items-center justify-end gap-2">
              <ActionButton tone="ghost" onClick={onClose}>
                Close
              </ActionButton>
              <ActionButton tone={full ? "danger" : "primary"}>
                {full ? "Join Waitlist" : "Confirm Reservation"}
              </ActionButton>
            </div>
          </motion.div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}
