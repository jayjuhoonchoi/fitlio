"use client";

type InlineStatusProps = {
  loading: boolean;
  error: string | null;
  empty: boolean;
  emptyLabel?: string;
};

export function InlineStatus({
  loading,
  error,
  empty,
  emptyLabel = "No data available."
}: InlineStatusProps): JSX.Element | null {
  if (loading) {
    return <p className="text-xs text-muted">Loading...</p>;
  }
  if (error) {
    return <p className="text-xs text-danger">{error}</p>;
  }
  if (empty) {
    return <p className="text-xs text-muted">{emptyLabel}</p>;
  }
  return null;
}
