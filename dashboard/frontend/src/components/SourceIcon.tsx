export function SourceIcon({ source }: { source: string }) {
  const cls = "w-4 h-4 flex-shrink-0";
  if (source === 'voicenotes') {
    return <img src="/icons/voicenotes.png" alt="VoiceNotes" className={cls} style={{ borderRadius: 3 }} />;
  }
  if (source === 'readwise') {
    return <img src="/icons/readwise.svg" alt="Readwise" className={cls} style={{ borderRadius: 3 }} />;
  }
  if (source === 'filesystem') {
    return (
      <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="#60a5fa" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z" />
      </svg>
    );
  }
  if (source === 'project_router') {
    return (
      <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="#34d399" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
      </svg>
    );
  }
  return (
    <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="#71717a" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
    </svg>
  );
}
