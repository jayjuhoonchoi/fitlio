"use client";

import { Component, type ErrorInfo, type ReactNode } from "react";

type SectionErrorBoundaryProps = {
  title: string;
  children: ReactNode;
};

type SectionErrorBoundaryState = {
  hasError: boolean;
};

export class SectionErrorBoundary extends Component<
  SectionErrorBoundaryProps,
  SectionErrorBoundaryState
> {
  state: SectionErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): SectionErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(_error: Error, _info: ErrorInfo): void {
    // Future: send to monitoring pipeline (Sentry/Datadog).
  }

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        <section className="rounded-xl2 border border-danger/45 bg-danger/10 p-4">
          <h2 className="text-sm font-semibold text-danger">
            {this.props.title} failed to render
          </h2>
          <p className="mt-1 text-xs text-muted">
            Isolated by section boundary. Other dashboard zones remain available.
          </p>
        </section>
      );
    }
    return this.props.children;
  }
}
