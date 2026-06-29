interface Props {
  id: string;
  name: string;
  type: string;
  label: string;
  placeholder: string;
  autoComplete: string;
  minLength?: number;
}

export function AuthField({
  id,
  name,
  type,
  label,
  placeholder,
  autoComplete,
  minLength,
}: Props) {
  return (
    <div>
      <label
        htmlFor={id}
        className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-white/50"
      >
        {label}
      </label>
      <input
        id={id}
        name={name}
        type={type}
        required
        minLength={minLength}
        placeholder={placeholder}
        autoComplete={autoComplete}
        className="w-full rounded-xl border border-white/10 bg-ink-900/60 px-4 py-2.5 text-sm text-white outline-none transition placeholder:text-white/25 focus:border-gilt/50 focus:ring-2 focus:ring-gilt/15"
      />
    </div>
  );
}
