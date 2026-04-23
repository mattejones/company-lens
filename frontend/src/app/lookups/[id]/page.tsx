"use client";
import { useEffect, useState } from "react";
import { use } from "react";
import { getLookup, verifyDomain, LookupDetail, DomainCandidate } from "@/lib/api";

export default function LookupPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [lookup, setLookup] = useState<LookupDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [verifying, setVerifying] = useState<string | null>(null);
  const [verified, setVerified] = useState<string | null>(null);

  useEffect(() => {
    getLookup(id).then((data) => {
      setLookup(data);
      if (data.verified_domain_id) {
        const v = data.candidates.find((c) => c.id === data.verified_domain_id);
        if (v) setVerified(v.domain);
      }
    }).finally(() => setLoading(false));
  }, [id]);

  async function handleVerify(domain: string) {
    if (!lookup) return;
    setVerifying(domain);
    try {
      await verifyDomain(id, domain);
      setVerified(domain);
      setLookup((l) => l ? { ...l, verified_by: "human" } : l);
    } finally {
      setVerifying(null);
    }
  }

  if (loading) return (
    <div className="flex items-center justify-center py-32">
      <div className="w-5 h-5 border border-accent/40 border-t-accent rounded-full animate-spin" />
    </div>
  );

  if (!lookup) return (
    <div className="text-center py-32 font-mono text-text-muted text-sm">Lookup not found</div>
  );

  const primaryCandidate = lookup.candidates.find((c) => c.is_primary_candidate);

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="mb-8">
        <p className="font-mono text-xs text-accent tracking-widest mb-2 uppercase">Lookup Result</p>
        <h1 className="font-display text-3xl font-700 text-text-primary mb-1">
          {lookup.company?.company_name ?? "Unknown Company"}
        </h1>
        <p className="font-mono text-xs text-text-muted">{lookup.company?.company_number}</p>
      </div>

      {/* Summary card */}
      {lookup.ranking_summary && (
        <div className="bg-bg-surface border border-accent/20 rounded p-5 mb-8 glow">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="font-mono text-xs text-text-muted mb-1">Primary domain</p>
              <p className="font-display text-2xl font-700 text-accent">
                {lookup.ranking_summary.primary_domain ?? "—"}
              </p>
              {verified && (
                <div className="flex items-center gap-2 mt-2">
                  <div className="status-dot success" />
                  <span className="font-mono text-xs text-status-success">Human verified: {verified}</span>
                </div>
              )}
            </div>
            {lookup.ranking_summary.summary && (
              <p className="text-xs text-text-secondary max-w-sm leading-relaxed hidden md:block">
                {lookup.ranking_summary.summary}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Candidates */}
      <div>
        <p className="font-mono text-xs text-text-muted uppercase tracking-widest mb-4">
          {lookup.candidates.length} domain candidates
        </p>
        <div className="stagger space-y-3">
          {lookup.candidates.map((c) => (
            <CandidateCard
              key={c.id}
              candidate={c}
              isVerified={verified === c.domain}
              verifying={verifying === c.domain}
              onVerify={() => handleVerify(c.domain)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function CandidateCard({
  candidate: c,
  isVerified,
  verifying,
  onVerify,
}: {
  candidate: DomainCandidate;
  isVerified: boolean;
  verifying: boolean;
  onVerify: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const score = c.final_score ?? 0;

  return (
    <div className={`bg-bg-surface border rounded transition-all ${
      isVerified ? "border-accent/40 bg-accent/5" :
      c.is_primary_candidate ? "border-accent/20" : "border-bg-border"
    }`}>
      {/* Main row */}
      <div className="p-4 flex items-center gap-4">
        {/* Score bar */}
        <div className="shrink-0 w-12 text-center">
          <div className="text-xs font-mono font-500 text-accent">
            {Math.round(score * 100)}
          </div>
          <div className="h-1 bg-bg-border rounded-full mt-1">
            <div
              className="h-1 bg-accent rounded-full transition-all"
              style={{ width: `${score * 100}%` }}
            />
          </div>
        </div>

        {/* Domain + badges */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-mono text-sm text-text-primary font-500">{c.domain}</span>
            {c.is_primary_candidate && (
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded border border-accent/30 text-accent bg-accent/10">
                primary
              </span>
            )}
            {c.discovered_via_redirect && (
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded border border-text-muted/30 text-text-muted">
                via redirect
              </span>
            )}
            {c.is_squatted_or_parked && (
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded border border-status-failure/30 text-status-failure bg-status-failure/10">
                parked
              </span>
            )}
            {isVerified && (
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded border border-status-success/30 text-status-success bg-status-success/10">
                ✓ verified
              </span>
            )}
          </div>

          {/* Signal pills */}
          <div className="flex items-center gap-3 mt-2">
            <Signal label="MX" value={c.dns_data?.mx_record} />
            <Signal label="A" value={c.dns_data?.a_record} />
            <Signal label="HTTPS" value={c.https_data?.live} />
            <Signal label="Parked" value={c.dns_data?.is_parked} invert />
          </div>
        </div>

        {/* Actions */}
        <div className="shrink-0 flex items-center gap-2">
          <button
            onClick={() => setExpanded((e) => !e)}
            className="px-3 py-1.5 text-xs font-mono text-text-secondary hover:text-text-primary border border-bg-border hover:border-accent/30 rounded transition-all"
          >
            {expanded ? "Less" : "More"}
          </button>
          {!isVerified && (
            <button
              onClick={onVerify}
              disabled={verifying}
              className="px-3 py-1.5 text-xs font-mono text-accent border border-accent/30 hover:bg-accent/10 rounded transition-all disabled:opacity-50"
            >
              {verifying ? "..." : "Verify ✓"}
            </button>
          )}
        </div>
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div className="border-t border-bg-border px-4 pb-4 pt-3 grid grid-cols-2 md:grid-cols-4 gap-4">
          <DetailBlock label="LLM confidence" value={`${Math.round((c.llm_confidence ?? 0) * 100)}%`} />
          <DetailBlock label="Verification" value={`${Math.round((c.verification_score ?? 0) * 100)}%`} />
          <DetailBlock label="SSL org" value={c.ssl_data?.org ?? "—"} />
          <DetailBlock label="Registrar" value={c.whois_data?.registrar ?? "—"} />
          {c.https_data?.redirect_domain && (
            <DetailBlock label="Redirects to" value={c.https_data.redirect_domain} />
          )}
          {c.content_data?.signals?.title && (
            <DetailBlock label="Page title" value={c.content_data.signals.title} className="col-span-2" />
          )}
          {c.ranking_reasoning && (
            <div className="col-span-2 md:col-span-4">
              <p className="font-mono text-xs text-text-muted mb-1">Ranking reasoning</p>
              <p className="text-xs text-text-secondary leading-relaxed">{c.ranking_reasoning}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Signal({ label, value, invert }: { label: string; value?: boolean; invert?: boolean }) {
  const active = invert ? !value : value;
  if (value === undefined || value === null) return null;
  return (
    <span className={`font-mono text-[10px] ${active ? "text-status-success" : "text-text-muted"}`}>
      {label}
    </span>
  );
}

function DetailBlock({ label, value, className }: { label: string; value: string; className?: string }) {
  return (
    <div className={className}>
      <p className="font-mono text-[10px] text-text-muted mb-0.5">{label}</p>
      <p className="font-mono text-xs text-text-primary truncate">{value}</p>
    </div>
  );
}
