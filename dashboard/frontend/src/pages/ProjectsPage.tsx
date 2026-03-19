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
      <div className="grid grid-cols-3 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-40 bg-zinc-900 border border-zinc-800 rounded-lg animate-pulse" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-zinc-800 border border-zinc-700 rounded-lg p-8 text-center text-zinc-400">
        Failed to load projects: {error}
      </div>
    );
  }

  if (projects.length === 0) {
    return (
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-12 text-center">
        <div className="text-zinc-500 text-lg mb-2">No projects</div>
        <div className="text-zinc-600 text-sm">Register projects in the project registry to see them here</div>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-3 gap-4">
      {projects.map((project) => (
        <Link
          key={project.key}
          to={`/projects/${project.key}`}
          className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 hover:border-zinc-700 hover:bg-zinc-800/50 transition-colors group"
        >
          <div className="flex items-start justify-between mb-2">
            <h3 className="text-lg font-medium text-zinc-100 group-hover:text-blue-400 transition-colors">
              {project.display_name || project.key}
            </h3>
            {project.language && (
              <span className="text-xs bg-zinc-800 border border-zinc-700 text-zinc-400 px-2 py-0.5 rounded">
                {project.language}
              </span>
            )}
          </div>

          {project.keywords && project.keywords.length > 0 && (
            <div className="flex flex-wrap gap-1 mb-3 max-h-16 overflow-hidden">
              {project.keywords.slice(0, 8).map((kw) => (
                <span
                  key={kw}
                  className="inline-flex px-1.5 py-0.5 rounded bg-zinc-800 text-xs text-zinc-400"
                >
                  {kw}
                </span>
              ))}
              {project.keywords.length > 8 && (
                <span className="text-xs text-zinc-600">+{project.keywords.length - 8}</span>
              )}
            </div>
          )}

          <div className="flex items-center gap-4 text-xs text-zinc-500 mt-auto">
            {project.active_notes !== undefined && (
              <span>{project.active_notes} active</span>
            )}
            {project.review_notes !== undefined && (
              <span>{project.review_notes} in review</span>
            )}
            {project.archived_notes !== undefined && (
              <span>{project.archived_notes} archived</span>
            )}
          </div>
        </Link>
      ))}
    </div>
  );
}
