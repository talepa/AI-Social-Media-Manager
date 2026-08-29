"use client";

import type { ResearchPlan } from "../lib/planTypes";
import { PLAN_TEMPLATE_LABELS } from "../lib/planTypes";

export default function PlanView({ plan }: { plan: ResearchPlan }) {
  const templateLabel = PLAN_TEMPLATE_LABELS[plan.template] ?? "Plan";

  return (
    <article className="plan-view">
      <header className="plan-view-head">
        <span className="plan-view-badge">{templateLabel}</span>
        <h3 className="plan-view-title">{plan.headline}</h3>
        <p className="plan-view-goal">{plan.goal}</p>
      </header>

      {plan.success_criteria.length > 0 && (
        <section className="plan-block">
          <h4 className="plan-block-title">Success looks like</h4>
          <ul className="plan-list">
            {plan.success_criteria.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
      )}

      {plan.sections.map((sec) => (
        <section key={sec.id} className="plan-block">
          <h4 className="plan-block-title">{sec.title}</h4>
          {sec.items.length > 0 && (
            <ul className="plan-list">
              {sec.items.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          )}
          {sec.steps.length > 0 && (
            <ol className="plan-steps">
              {sec.steps.map((step) => (
                <li key={step.title} className="plan-step">
                  <div className="plan-step-head">
                    <span className="plan-step-title">{step.title}</span>
                    {step.timeframe ? (
                      <span className="plan-step-time">{step.timeframe}</span>
                    ) : null}
                  </div>
                  <p className="plan-step-detail">{step.detail}</p>
                </li>
              ))}
            </ol>
          )}
          {sec.resources.length > 0 && (
            <ul className="plan-resources">
              {sec.resources.map((res) => (
                <li key={res.url}>
                  <a href={res.url} target="_blank" rel="noopener noreferrer" className="plan-resource-link">
                    <span className="plan-resource-kind">{res.kind}</span>
                    <span className="plan-resource-title">{res.title}</span>
                  </a>
                  {res.note ? <p className="plan-resource-note">{res.note}</p> : null}
                </li>
              ))}
            </ul>
          )}
        </section>
      ))}

      {plan.next_actions.length > 0 && (
        <section className="plan-block plan-block--actions">
          <h4 className="plan-block-title">This week</h4>
          <ul className="plan-checklist">
            {plan.next_actions.map((action) => (
              <li key={action}>
                <span className="plan-check" aria-hidden />
                {action}
              </li>
            ))}
          </ul>
        </section>
      )}
    </article>
  );
}
