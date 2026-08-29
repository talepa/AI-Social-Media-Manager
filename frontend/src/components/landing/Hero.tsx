"use client";

import Link from "next/link";
import { InvestigationPreview } from "./InvestigationPreview";

export function Hero() {
  return (
    <section className="grid flex-1 gap-10 px-5 py-12 md:grid-cols-2 md:gap-12 md:px-8 md:py-16 lg:py-20">
      <div className="flex flex-col justify-center">
        <p className="obs-kicker mb-6">Atelier / 01</p>
        <h1 className="obs-display text-4xl md:text-5xl lg:text-6xl">
          Technical
          <br />
          Intelligence
        </h1>
        <p
          className="mt-6 max-w-md text-base md:text-lg"
          style={{ color: "var(--graphite)", lineHeight: 1.55 }}
        >
          Turn a difficult technical question into an evidence-backed decision.
        </p>
        <div className="mt-10 flex flex-wrap gap-3">
          <Link href="/commission" className="obs-btn">
            Start investigation
          </Link>
          <a href="#pipeline" className="obs-btn obs-btn-ghost">
            View pipeline
          </a>
        </div>
        <hr className="obs-rule mt-12 max-w-sm" />
        <p className="obs-mono mt-4 text-[0.65rem] tracking-[0.12em] text-[var(--muted)]">
          Director → Specialists → MCP → Evidence → Report
        </p>
      </div>
      <InvestigationPreview />
    </section>
  );
}
