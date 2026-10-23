import type { Dashboard, Locale } from "../../impact/content";
import { DefinitionDetails, words } from "../../impact/content";

const number = (value: number | null | undefined, locale: Locale, unavailable: string) => value === null || value === undefined ? unavailable : value.toLocaleString(locale, { maximumFractionDigits: 2 });
export function Evidence({ dashboard, locale }: { dashboard: Dashboard; locale: Locale }) {
  const t = words[locale];
  const groups = ["marketing", "program", "learning", "entrepreneurship", "funding", "support", "impact"];
  const labels = { marketing: t.marketing, program: t.programGroup, learning: t.learning, entrepreneurship: t.entrepreneurship, funding: t.funding, support: t.support, impact: t.impact };
  return <><dl className="impact-facts"><div><dt>{t.from}</dt><dd>{dashboard.filters.from_date}</dd></div><div><dt>{t.through}</dt><dd>{dashboard.filters.through_date}</dd></div>
    <div><dt>{t.generated}</dt><dd><time dateTime={dashboard.generated_at}>{new Date(dashboard.generated_at).toLocaleString(locale)}</time></dd></div>
    <div><dt>{t.dictionary}</dt><dd>{dashboard.dictionary_version}</dd></div></dl>
    {(dashboard.filters.program_id || dashboard.filters.cohort_id) && <p>{t.program}: {dashboard.filters.program_id ?? t.allPrograms} · {t.cohort}: {dashboard.filters.cohort_id ?? t.allCohorts}</p>}
    <p className="impact-warning">{locale === "ta" ? dashboard.caveat_ta : dashboard.caveat_en}</p>
    {groups.map((group) => <section key={group} aria-label={labels[group as keyof typeof labels]} className="impact-panel"><h2>{labels[group as keyof typeof labels]}</h2>
      {dashboard.metrics.some((metric) => metric.group === group) && <div className="impact-table"><table><thead><tr><th scope="col">{t.measure}</th><th scope="col">{t.value}</th><th scope="col">{t.details}</th></tr></thead>
        <tbody>{dashboard.metrics.filter((metric) => metric.group === group).map((metric) => <tr key={metric.key}><th scope="row">{locale === "ta" ? metric.label_ta : metric.label_en}</th>
          <td className={metric.value != null ? "impact-number" : undefined}>{number(metric.value, locale, t.unavailable)}{metric.value !== null && metric.value !== undefined && metric.unit === "percent" ? "%" : ""}</td>
          <td><details><summary>{t.details}</summary><p>{locale === "ta" ? metric.definition_ta : metric.definition_en}</p>
            <dl><dt>{t.source}</dt><dd>{metric.source}</dd><dt>{t.basis}</dt><dd>{metric.temporal_basis}</dd><dt>{t.unit}</dt><dd>{metric.unit in t ? t[metric.unit as "hours" | "count" | "percent" | "INR"] : metric.unit}</dd><dt>{t.numerator}</dt><dd>{number(metric.numerator, locale, t.unavailable)}</dd><dt>{t.denominator}</dt><dd>{number(metric.denominator, locale, t.unavailable)}</dd></dl>
            {(locale === "ta" ? metric.caveat_ta : metric.caveat_en) && <p className="impact-warning">{locale === "ta" ? metric.caveat_ta : metric.caveat_en}</p>}
            {!!metric.breakdown?.length && <ul>{metric.breakdown.map((item) => <li key={item.key}>{item.label}: <strong>{item.count}</strong><div className="impact-bar" aria-hidden="true"><span style={{ width: `${Math.min(100, Math.max(0, item.count / Math.max(1, ...(metric.breakdown ?? []).map((entry) => entry.count)) * 100))}%` }} /></div></li>)}</ul>}
          </details></td></tr>)}</tbody></table></div>}
      {group === "impact" && <><h3>{t.coverage}</h3><dl className="impact-facts"><div><dt>{t.eligible}</dt><dd>{dashboard.eligible_impact_enrollments}</dd></div>
        <div><dt>{t.reported}</dt><dd>{dashboard.impact_reported_enrollments}</dd></div><div><dt>{t.coverage}</dt><dd>{number(dashboard.impact_coverage, locale, t.unavailable)}{dashboard.impact_coverage !== null ? "%" : ""}</dd></div></dl>
        <h3>{t.impactByEdition}</h3>{!dashboard.impact.length && <p>{t.noImpact}</p>}
        {dashboard.impact.map((item) => <article key={item.definition.id}><DefinitionDetails definition={item.definition} locale={locale} />
          <dl className="impact-facts"><div><dt>{t.eligible}</dt><dd>{item.eligible_enrollments}</dd></div><div><dt>{t.baseline}</dt><dd>{item.baseline_reported}</dd></div><div><dt>{t.outcome}</dt><dd>{item.outcome_reported}</dd></div>
            <div><dt>{t.matched}</dt><dd>{item.matched_sample}</dd></div><div><dt>{t.baselineJobs}</dt><dd>{item.baseline_jobs}</dd></div><div><dt>{t.outcomeJobs}</dt><dd>{item.outcome_jobs}</dd></div>
            <div><dt>{t.matchedChange}</dt><dd>{number(item.matched_jobs_change, locale, t.unavailable)}</dd></div><div><dt>{t.started}</dt><dd>{item.outcome_started}</dd></div><div><dt>{t.active}</dt><dd>{item.outcome_active}</dd></div></dl>
          <p className="impact-warning">{locale === "ta" ? item.caveat_ta : item.caveat_en}</p></article>)}
      </>}
    </section>)}
  </>;
}

export function Comparison({ current, previous, locale }: { current: Dashboard; previous: Dashboard; locale: Locale }) {
  const t = words[locale]; const prior = new Map(previous.metrics.map((item) => [item.key, item]));
  const impactIds = [...new Set([...current.impact, ...previous.impact].map((item) => item.definition.id))];
  const row = (label: string, present: number | null | undefined, before: number | null | undefined, comparable = true) => <tr key={label}><th scope="row">{label}</th><td className={present != null ? "impact-number" : undefined}>{number(present, locale, t.unavailable)}</td><td className={before != null ? "impact-number" : undefined}>{number(before, locale, t.unavailable)}</td><td className={comparable && present != null && before != null ? "impact-number" : undefined}>{comparable && present != null && before != null ? number(present - before, locale, t.unavailable) : t.unavailable}</td></tr>;
  return <section className="impact-panel"><h2>{t.comparison}</h2>
    <p>{t.current}: {current.filters.from_date} — {current.filters.through_date} · {t.dictionary} {current.dictionary_version} · {current.generated_at}</p>
    <p>{t.program}: {current.filters.program_id ?? t.allPrograms} · {t.cohort}: {current.filters.cohort_id ?? t.allCohorts}</p>
    <p>{t.previous}: {previous.filters.from_date} — {previous.filters.through_date} · {t.dictionary} {previous.dictionary_version} · {previous.generated_at}</p>
    <p>{t.program}: {previous.filters.program_id ?? t.allPrograms} · {t.cohort}: {previous.filters.cohort_id ?? t.allCohorts}</p>
    <p>{t.edition}: {previous.impact.map((item) => item.definition.edition).join(", ") || t.unavailable}</p>
    <p className="impact-warning">{t.comparisonCaveat}</p>
    <div className="impact-table"><table><thead><tr><th>{t.measure}</th><th>{t.current}</th><th>{t.previous}</th><th>{t.difference}</th></tr></thead><tbody>
      {current.metrics.map((item) => { const old = prior.get(item.key); const comparable = current.dictionary_version === previous.dictionary_version && old?.unit === item.unit && item.value != null && old?.value != null;
        return <tr key={item.key}><th scope="row">{locale === "ta" ? item.label_ta : item.label_en}</th><td className={item.value != null ? "impact-number" : undefined}>{number(item.value, locale, t.unavailable)}</td><td className={old?.value != null ? "impact-number" : undefined}>{number(old?.value, locale, t.unavailable)}</td><td className={comparable ? "impact-number" : undefined}>{comparable ? number(item.value! - old!.value!, locale, t.unavailable) : t.unavailable}</td></tr>; })}
    </tbody></table></div>
    <h3>{t.coverage}</h3><div className="impact-table"><table><thead><tr><th>{t.measure}</th><th>{t.current}</th><th>{t.previous}</th><th>{t.difference}</th></tr></thead><tbody>
      {row(t.eligible, current.eligible_impact_enrollments, previous.eligible_impact_enrollments)}
      {row(t.reported, current.impact_reported_enrollments, previous.impact_reported_enrollments)}
      {row(t.coverage, current.impact_coverage, previous.impact_coverage)}
    </tbody></table></div>
    {impactIds.map((id) => { const present = current.impact.find((item) => item.definition.id === id); const before = previous.impact.find((item) => item.definition.id === id); const edition = present?.definition ?? before!.definition;
      const comparable = current.dictionary_version === previous.dictionary_version && present?.definition.edition === before?.definition.edition;
      return <article key={id}><h3>{t.edition} {edition.edition}: {locale === "ta" ? edition.title_ta : edition.title_en}</h3>
        <div className="impact-table"><table><thead><tr><th>{t.measure}</th><th>{t.current}</th><th>{t.previous}</th><th>{t.difference}</th></tr></thead><tbody>
          {row(t.eligible, present?.eligible_enrollments, before?.eligible_enrollments, comparable)}
          {row(t.baseline, present?.baseline_reported, before?.baseline_reported, comparable)}
          {row(t.outcome, present?.outcome_reported, before?.outcome_reported, comparable)}
          {row(t.matched, present?.matched_sample, before?.matched_sample, comparable)}
          {row(t.matchedBaselineJobs, present?.matched_baseline_jobs, before?.matched_baseline_jobs, comparable)}
          {row(t.matchedOutcomeJobs, present?.matched_outcome_jobs, before?.matched_outcome_jobs, comparable)}
          {row(t.matchedChange, present?.matched_jobs_change, before?.matched_jobs_change, comparable)}
          {row(t.started, present?.outcome_started, before?.outcome_started, comparable)}
          {row(t.active, present?.outcome_active, before?.outcome_active, comparable)}
        </tbody></table></div></article>;
    })}
  </section>;
}
