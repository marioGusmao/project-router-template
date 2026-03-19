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
          <div key={i} className="h-48 bg-zinc-900/80 border border-zinc-800/60 rounded-xl animate-pulse" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-zinc-900/80 border border-zinc-800/60 rounded-xl p-8 text-center text-zinc-400">
        Failed to load projects: {error}
      </div>
    );
  }

  if (projects.length === 0) {
    return (
      <div className="bg-zinc-900/80 border border-zinc-800/60 rounded-xl p-16 text-center">
        <div className="text-zinc-400 text-lg font-medium mb-2">No projects</div>
        <div className="text-zinc-600 text-sm">Register projects in the project registry to see them here</div>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
      {projects.map((project) => (
        <Link
          key={project.key}
          to={`/projects/${project.key}`}
          className="block bg-zinc-900/50 border border-zinc-800/40 rounded-xl p-6 hover:border-zinc-700/60 hover:bg-zinc-900/70 transition-all group"
        >
          <div className="flex items-start justify-between mb-3">
            <h3 className="text-xl font-semibold text-zinc-100 group-hover:text-blue-400 transition-colors tracking-tight">
              {project.display_name || project.key}
            </h3>
            {project.language && (
              <span className="text-[11px] font-medium bg-zinc-800/80 border border-zinc-700/50 text-zinc-400 px-2.5 py-1 rounded-full flex-shrink-0 ml-3">
                {project.language}
              </span>
            )}
          </div>

          {project.keywords && project.keywords.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mb-4">
              {project.keywords.slice(0, 8).map((kw) => (
                <span
                  key={kw}
                  className="inline-flex px-2 py-0.5 rounded bg-zinc-800/80 text-xs text-zinc-400"
                >
                  {kw}
                </span>
              ))}
              {project.keywords.length > 8 && (
                <span className="text-xs text-zinc-600 self-center">+{project.keywords.length - 8}</span>
              )}
            </div>
          )}

          <div className="flex items-center gap-5 text-sm text-zinc-500 mt-auto pt-2 border-t border-zinc-800/40">
            {project.active_notes !== undefined && (
              <span>
                <span className="text-blue-400 font-semibold tabular-nums">{project.active_notes}</span> active
              </span>
            )}
            {project.review_notes !== undefined && (
              <span>
                <span className="text-amber-400 font-semibold tabular-nums">{project.review_notes}</span> in review
              </span>
            )}
            {project.archived_notes !== undefined && (
              <span>
                <span className="text-zinc-400 font-semibold tabular-nums">{project.archived_notes}</span> archived
              </span>
            )}
          </div>
        </Link>
      ))}
    </div>
  );
}
