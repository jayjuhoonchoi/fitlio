export type MemberLevel = "starter" | "core" | "elite" | "vip";

export type Member = {
  id: string;
  memberNo: string;
  name: string;
  email: string;
  phone: string;
  level: MemberLevel;
  active: boolean;
  attendanceRate: number;
  streakDays: number;
};

export type ClassSlot = {
  id: string;
  title: string;
  coach: string;
  startsAt: string;
  capacity: number;
  booked: number;
  waitlist: number;
};

export type WaitlistEntry = {
  id: string;
  memberNo: string;
  memberName: string;
  requestedAt: string;
  status: "waiting" | "promoted";
};

export type RevenuePoint = {
  month: string;
  mrr: number;
  retention: number;
  occupancy: number;
};

export type CohortPoint = {
  cohort: string;
  m1: number;
  m2: number;
  m3: number;
  m6: number;
};

export type WhiteLabelSiteConfig = {
  centerName: string;
  subdomain: string;
  headline: string;
  body: string;
};
