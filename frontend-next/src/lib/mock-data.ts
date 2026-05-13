import type {
  ClassSlot,
  CohortPoint,
  Member,
  RevenuePoint,
  WaitlistEntry,
  WhiteLabelSiteConfig
} from "@/types/domain";

export const members: Member[] = [
  {
    id: "m-1",
    memberNo: "FT-1021",
    name: "Jay Choi",
    email: "jay.choi@fitlio.com",
    phone: "+82-10-1000-2000",
    level: "vip",
    active: true,
    attendanceRate: 88,
    streakDays: 9
  },
  {
    id: "m-2",
    memberNo: "FT-1199",
    name: "Mina Park",
    email: "mina.park@fitlio.com",
    phone: "+82-10-3000-2000",
    level: "core",
    active: true,
    attendanceRate: 42,
    streakDays: 1
  },
  {
    id: "m-3",
    memberNo: "FT-1400",
    name: "Chris Lee",
    email: "chris.lee@fitlio.com",
    phone: "+61-414-123-333",
    level: "elite",
    active: false,
    attendanceRate: 36,
    streakDays: 0
  }
];

export const classSlots: ClassSlot[] = [
  {
    id: "c-001",
    title: "HIIT 45",
    coach: "Sora Kim",
    startsAt: "2026-05-13T19:30:00Z",
    capacity: 20,
    booked: 18,
    waitlist: 5
  },
  {
    id: "c-002",
    title: "Pilates Core",
    coach: "Jay Choi",
    startsAt: "2026-05-13T22:00:00Z",
    capacity: 16,
    booked: 16,
    waitlist: 3
  },
  {
    id: "c-003",
    title: "Strength Base",
    coach: "Mia Song",
    startsAt: "2026-05-14T00:00:00Z",
    capacity: 20,
    booked: 11,
    waitlist: 0
  }
];

export const waitlistEntries: WaitlistEntry[] = [
  {
    id: "w-1",
    memberNo: "FT-2088",
    memberName: "Ethan Han",
    requestedAt: "2026-05-13T08:12:00Z",
    status: "waiting"
  },
  {
    id: "w-2",
    memberNo: "FT-1802",
    memberName: "Sujin Yoo",
    requestedAt: "2026-05-13T08:15:00Z",
    status: "promoted"
  }
];

export const revenueTrend: RevenuePoint[] = [
  { month: "Jan", mrr: 86000, retention: 77, occupancy: 61 },
  { month: "Feb", mrr: 91000, retention: 79, occupancy: 65 },
  { month: "Mar", mrr: 97000, retention: 80, occupancy: 69 },
  { month: "Apr", mrr: 110000, retention: 82, occupancy: 73 },
  { month: "May", mrr: 126840, retention: 84.7, occupancy: 78 }
];

export const cohortData: CohortPoint[] = [
  { cohort: "2026-01", m1: 100, m2: 88, m3: 77, m6: 62 },
  { cohort: "2026-02", m1: 100, m2: 91, m3: 79, m6: 66 },
  { cohort: "2026-03", m1: 100, m2: 89, m3: 81, m6: 71 }
];

export const whiteLabelSiteDefault: WhiteLabelSiteConfig = {
  centerName: "Fitlio CBD Flagship",
  subdomain: "cbd.fitlio.app",
  headline: "Train Smarter. Recover Better.",
  body: "Premium classes, world-class coaches, and measurable progress. Build your strongest routine with Fitlio."
};
