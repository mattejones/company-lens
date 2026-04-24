"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { listJobs, JobStatus } from "@/lib/api";

const statusStyle: Record<string, string> = {
  SUCCESS: "text-status-success border-status-success/30 bg-status-success/10",
  PENDING: "text-status-pending border-status-pending/30 bg-status-pending/10",
  STARTED: "text-status-pending border-status-pending/30 bg-status-pending/10",
  FAILURE: "text-status-failure border-status-failure/30 bg-status-failure/10",
};

export default function JobsPage() {
  const [jobs, setJobs] = useState<JobStatus[]>([]);
  const [loading, setLoading] = useState(true);

  async function load() {
    try { setJobs(await listJobs()); } finally { setLoading(false); }
  }

  useEffect(() => {
    load();
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="animate-fade-in">
      <div className="mb-8 flex items-end justify-between">
        <div>
          <p className="font-mono text-xs text-accent tracking-widest mb-2 uppercase">Pipeline</p>
          <h1 className="font-display text-3xl font-700 text-text-primary">Jobs</h1>
        </div>
        <p className="font-mono text-xs text-text-muted">Auto-refreshes every 5s</p>
      </div>

      {loading ? (
        <div className="text-center py-16"><div className="w-5 h-5 border border-accent/40 border-t-accent rounded-full animate-spin mx-auto" /></div>
      ) : jobs.length === 0 ? (
        <div className="border border-dashed border-bg-border rounded p-16 text-center">
          <p className="font-mono text-xs text-text-muted">No jobs yet — search for a company and enrich it</p>
        </div>
      ) : (
        <div className="stagger space-y-2">
          {jobs.map((job) => <JobRow key={job.job_id} job={job} />)}
        </div>
      )}
    </div>
  );
}

function JobRow({ job }: { job: JobStatus }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="bg-bg-surface border border-bg-border rounded hover:border-accent/20 transition-all">
      <div className="p-4 flex items-start gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-3 mb-1 flex-wrap">
            <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${statusStyle[job.status] ?? ""}`}>
              {job.status}
            </span>
            <span className="font-mono text-[10px] text-text-muted">{job.type}</span>
          </div>
          <p className="font-display font-500 text-text-primary text-sm">
            {job.company_name ?? job.company_number ?? job.job_id}
          </p>
          <div className="flex flex-wrap gap-x-4 mt-1">
            <span className="font-mono text-[10px] text-text-muted">ID: {job.job_id}</span>
            {job.created_at && (
              <span className="font-mono text-[10px] text-text-muted">{new Date(job.created_at).toLocaleString()}</span>
            )}
            {job.lookup_id && (
              <span className="font-mono text-[10px] text-accent">Lookup: {job.lookup_id}</span>
            )}
          </div>
          {job.error && (
            <p className="text-xs font-mono text-status-failure mt-1 break-all">{job.error}</p>
          )}
        </div>

        <div className="shrink-0 flex items-center gap-2 pt-0.5">
          <button onClick={() => setExpanded((e) => !e)}
            className="px-3 py-1.5 text-xs font-mono text-text-muted border border-bg-border hover:border-accent/30 hover:text-text-secondary rounded transition-all">
            {expanded ? "Less ▲" : "Raw ▼"}
          </button>
          {job.lookup_id && job.status === "SUCCESS" && (
            <Link href={`/lookups/${job.lookup_id}`}
              className="px-4 py-2 border border-accent/30 text-accent text-xs font-mono rounded hover:bg-accent/10 transition-all">
              View →
            </Link>
          )}
        </div>
      </div>

      {expanded && (
        <div className="border-t border-bg-border px-4 py-3">
          <pre className="text-[11px] font-mono text-text-secondary leading-relaxed overflow-x-auto whitespace-pre-wrap break-all">
            {JSON.stringify(job, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
