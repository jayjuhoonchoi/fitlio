export function AppLogo(): JSX.Element {
  return (
    <div className="flex items-center gap-2">
      <div className="h-8 w-8 rounded-xl bg-gradient-to-br from-accent to-silver" />
      <div className="leading-tight">
        <p className="text-sm font-semibold text-text">Fitlio</p>
        <p className="text-[11px] text-muted">Premium Studio OS</p>
      </div>
    </div>
  );
}
