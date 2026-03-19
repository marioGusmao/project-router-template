import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getProjects, type Project } from '../lib/api';

export function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const res = await getProjects();
        setProjects(res.projects ?? []);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="card animate-pulse"
            style={{ height: 200, animationDelay: `${i * 100}ms` }}
          />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="card" style={{ padding: 48, textAlign: 'center', color: '#a1a1aa' }}>
        Failed to load projects: {error}
      </div>
    );
  }

  if (projects.length === 0) {
    return (
      <div className="card" style={{ padding: 64, textAlign: 'center' }}>
        <div className="text-zinc-400 text-lg font-medium" style={{ marginBottom: 8 }}>
          No projects
        </div>
        <div className="text-zinc-600 text-sm">
          Register projects in the project registry to see them here
        </div>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
      {projects.map((project, i) => (
        <Link
          key={project.key}
          to={`/projects/${project.key}`}
          className="block card animate-in group relative overflow-hidden"
          style={{
            padding: 24,
            animationDelay: `${i * 80}ms`,
            transition: 'transform 0.2s ease, border-color 0.2s ease',
          }}
          onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.transform = 'scale(1.01)'; }}
          onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.transform = 'scale(1)'; }}
        >
          <div className="flex items-start justify-between" style={{ marginBottom: 12 }}>
            <h3
              className="text-zinc-100 group-hover:text-blue-400 transition-colors tracking-tight"
              style={{ fontSize: 22, fontWeight: 700 }}
            >
              {project.display_name || project.key}
            </h3>
            {project.language && (
              <span
                className="text-blue-400 font-medium flex-shrink-0"
                style={{
                  fontSize: 11,
                  background: 'rgba(59,130,246,0.1)',
                  padding: '3px 10px',
                  borderRadius: 9999,
                  marginLeft: 12,
                }}
              >
                {project.language}
              </span>
            )}
          </div>

          {project.keywords && project.keywords.length > 0 && (
            <div className="flex flex-wrap gap-1.5" style={{ marginBottom: 16 }}>
              {project.keywords.slice(0, 8).map((kw) => (
                <span
                  key={kw}
                  className="inline-flex font-mono text-zinc-500"
                  style={{
                    fontSize: 11,
                    background: 'rgba(255,255,255,0.04)',
                    border: '1px solid rgba(255,255,255,0.04)',
                    padding: '4px 8px',
                    borderRadius: 6,
                  }}
                >
                  {kw}
                </span>
              ))}
              {project.keywords.length > 8 && (
                <span className="text-zinc-600 self-center" style={{ fontSize: 12 }}>
                  +{project.keywords.length - 8}
                </span>
              )}
            </div>
          )}

          <div
            className="flex items-center gap-5 text-sm text-zinc-500"
            style={{ paddingTop: 12, borderTop: '1px solid rgba(255,255,255,0.06)', marginTop: 'auto' }}
          >
            {project.note_count !== undefined && (
              <span>
                <span className="text-emerald-400 font-semibold tabular-nums">{project.note_count}</span> notes
              </span>
            )}
            {project.review_count !== undefined && (
              <span>
                <span className="text-amber-400 font-semibold tabular-nums">{project.review_count}</span> in review
              </span>
            )}
          </div>
        </Link>
      ))}
    </div>
  );
}
