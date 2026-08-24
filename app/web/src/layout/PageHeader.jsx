export function PageHeader({ title, subtitle, children }) {
    return (
        <div className="mb-5 flex flex-wrap items-end gap-4">
            <div className="min-w-0">
                <h1 className="text-[24px] font-semibold leading-tight tracking-tight">{title}</h1>
                {subtitle ? (
                    <p className="mt-1.5 max-w-[70ch] text-[14px] text-muted-foreground">{subtitle}</p>
                ) : null}
            </div>
            <div className="grow" />
            {children}
        </div>
    );
}
