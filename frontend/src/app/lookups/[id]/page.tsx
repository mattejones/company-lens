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

  return (
    <div className="animate-fade-in">
      <div className="mb-8">
        <p className="font-mono text-xs text-accent tracking-widest mb-2 uppercase">Lookup Result</p>
        <h1 className="font-display text-3xl font-700 text-text-primary mb-1">
          {lookup.company?.company_name ?? "Unknown Company"}
        </h1>
        <p className="font-mono text-xs text-text-muted">{lookup.company?.company_number}</p>
      </div>

      {lookup.ranking_summary && (
        <div className="bg-bg-surface border border-accent/20 rounded p-5 mb-8 glow">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="font-mono text-xs text-text-muted mb-1">Primary domain</p>
              <a
                href={`https://${lookup.ranking_summary.primary_domain}`}
                target="_blank"
                rel="noopener noreferrer"
                className="font-display text-2xl font-700 text-accent hover:underline"
              >
                {lookup.ranking_summary.primary_domain ?? "—"}
              </a>
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

  // A domain is "unresolved" if it has no A record and no HTTPS — not the same as parked
  const isUnresolved = c.dns_data?.a_record === false && c.https_data?.live === false && !c.dns_data?.is_parked;
  const contentScore = c.content_data?.match_score;

  return (
    <div className={`bg-bg-surface border rounded transition-all ${
      isVerified ? "border-accent/40 bg-accent/5" :
      c.is_primary_candidate ? "border-accent/20" : "border-bg-border"
    }`}>
      <div className="p-4 flex items-center gap-4">
        {/* Score */}
        <div className="shrink-0 w-12 text-center">
          <div className="text-xs font-mono font-500 text-accent">{Math.round(score * 100)}</div>
          <div className="h-1 bg-bg-border rounded-full mt-1">
            <div className="h-1 bg-accent rounded-full transition-all" style={{ width: `${score * 100}%` }} />
          </div>
        </div>

        {/* Domain + badges */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            {/* Clickable domain link */}
            <a
              href={`https://${c.domain}`}
              target="_blank"
              rel="noopener noreferrer"
              className="font-mono text-sm text-text-primary font-500 hover:text-accent transition-colors"
            >
              {c.domain} ↗
            </a>
            {c.is_primary_candidate && (
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded border border-accent/30 text-accent bg-accent/10">primary</span>
            )}
            {c.discovered_via_redirect && (
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded border border-text-muted/30 text-text-muted">via redirect</span>
            )}
            {/* parked badge only from LLM verdict */}
            {c.is_squatted_or_parked && (
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded border border-status-failure/30 text-status-failure bg-status-failure/10">parked / squatted</span>
            )}
            {/* unresolved — separate from parked */}
            {isUnresolved && (
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded border border-text-muted/30 text-text-muted">unresolved</span>
            )}
            {isVerified && (
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded border border-status-success/30 text-status-success bg-status-success/10">✓ verified</span>
            )}
          </div>

          {/* Signal pills */}
          <div className="flex items-center gap-3 mt-2 flex-wrap">
            <Signal label="MX" value={c.dns_data?.mx_record} />
            <Signal label="A record" value={c.dns_data?.a_record} />
            <Signal label="HTTPS" value={c.https_data?.live} />
            {/* Parked as a signal — shown as negative when true */}
            {c.dns_data?.is_parked !== undefined && (
              <span className={`font-mono text-[10px] ${c.dns_data.is_parked ? "text-status-failure" : "text-text-muted"}`}>
                {c.dns_data.is_parked ? "Parked NS" : "Clean NS"}
              </span>
            )}
            {/* Content match score */}
            {contentScore !== undefined && contentScore !== null && (
              <span className={`font-mono text-[10px] ${contentScore > 0.6 ? "text-status-success" : contentScore > 0.3 ? "text-status-pending" : "text-text-muted"}`}>
                Content {Math.round(contentScore * 100)}%
              </span>
            )}
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

      {expanded && (
        <div className="border-t border-bg-border px-4 pb-4 pt-3 grid grid-cols-2 md:grid-cols-4 gap-4">
          <DetailBlock label="LLM confidence" value={`${Math.round((c.llm_confidence ?? 0) * 100)}%`} />
          <DetailBlock label="Verification score" value={`${Math.round((c.verification_score ?? 0) * 100)}%`} />
          <DetailBlock label="SSL org" value={c.ssl_data?.org ?? "—"} />
          <DetailBlock label="Registrar" value={c.whois_data?.registrar ?? "—"} />
          {c.whois_data?.creation_date && (
            <DetailBlock label="Domain created" value={String(c.whois_data.creation_date).split("T")[0]} />
          )}
          {c.https_data?.redirect_domain && (
            <DetailBlock label="Redirects to" value={c.https_data.redirect_domain} />
          )}
          {c.ssl_data?.sans && c.ssl_data.sans.length > 0 && (
            <div className="col-span-2">
              <p className="font-mono text-[10px] text-text-muted mb-1">SSL SANs</p>
              <div className="flex flex-wrap gap-1">
                {c.ssl_data.sans.map((san) => (
                  <span key={san} className="font-mono text-[10px] px-1.5 py-0.5 bg-bg-elevated border border-bg-border rounded text-text-secondary">{san}</span>
                ))}
              </div>
            </div>
          )}
          {c.content_data?.signals?.title && (
            <DetailBlock label="Page title" value={c.content_data.signals.title} className="col-span-2" />
          )}
          {contentScore !== undefined && contentScore !== null && (
            <DetailBlock label="Content match score" value={`${Math.round(contentScore * 100)}%`} />
          )}
          {c.llm_reasoning && (
            <div className="col-span-2 md:col-span-4">
              <p className="font-mono text-[10px] text-text-muted mb-1">LLM reasoning</p>
              <p className="text-xs text-text-secondary leading-relaxed">{c.llm_reasoning}</p>
            </div>
          )}
          {c.ranking_reasoning && (
            <div className="col-span-2 md:col-span-4">
              <p className="font-mono text-[10px] text-text-muted mb-1">Ranking reasoning</p>
              <p className="text-xs text-text-secondary leading-relaxed">{c.ranking_reasoning}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Signal({ label, value }: { label: string; value?: boolean }) {
  if (value === undefined || value === null) return null;
  return (
    <span className={`font-mono text-[10px] ${value ? "text-status-success" : "text-text-muted"}`}>
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
