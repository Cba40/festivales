interface SectionTabsProps<T extends string> {
  sections: { key: T; label: string }[];
  activeSection: T;
  onChange: (section: T) => void;
  className?: string;
}

export function SectionTabs<T extends string>({
  sections,
  activeSection,
  onChange,
  className = 'flex gap-2 mb-6',
}: SectionTabsProps<T>) {
  return (
    <div className={className}>
      {sections.map((section) => (
        <button
          key={section.key}
          onClick={() => onChange(section.key)}
          className={`text-sm font-medium px-4 py-2 rounded-lg transition-colors ${
            activeSection === section.key
              ? 'bg-indigo-600 text-white'
              : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
          }`}
        >
          {section.label}
        </button>
      ))}
    </div>
  );
}