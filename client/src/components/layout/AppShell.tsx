import type { ReactNode } from "react";
import { SampleBanner, type BannerMode } from "./SampleBanner.tsx";

export type View = "overview" | "analyse";

interface Props {
  readonly mode: BannerMode;
  readonly apiOrigin?: string;
  readonly view: View;
  readonly onView: (view: View) => void;
  readonly children: ReactNode;
}

/** Banner, branding, navigation and footer. The banner is rendered here, above every page, and cannot be dismissed. */
export function AppShell({ mode, apiOrigin, view, onView, children }: Props) {
  return (
    <>
      <SampleBanner mode={mode} {...(apiOrigin === undefined ? {} : { apiOrigin })} />
      <a className="skip" href="#main">
        Skip to main content
      </a>
      <header className="shell-head">
        <div className="shell-head__inner">
          <div className="brand">
            <svg className="brand__mark" viewBox="0 0 24 24" width="28" height="28" aria-hidden="true" focusable="false">
              <path d="M12 2 4 5v6c0 5 3.4 9.4 8 11 4.6-1.6 8-6 8-11V5l-8-3Z" className="brand__shield" />
              <path d="m8.5 12.2 2.4 2.4 4.8-5" className="brand__tick" />
            </svg>
            <span className="brand__name">FinGuard</span>
          </div>
          <nav aria-label="Primary">
            <button type="button" className="nav-btn" aria-current={view === "overview" ? "page" : undefined} onClick={() => onView("overview")}>
              Overview
            </button>
            <button type="button" className="nav-btn" aria-current={view === "analyse" ? "page" : undefined} onClick={() => onView("analyse")}>
              Buy or wait?
            </button>
          </nav>
        </div>
      </header>
      <main id="main" tabIndex={-1}>
        {children}
      </main>
      <footer className="shell-foot">
        <p>
          FinGuard&apos;s deterministic engine is the only source of financial outcomes. This interface displays them; it does not
          calculate, rank or forecast.{" "}
          {mode === "mock"
            ? "Every figure on screen is invented sample data."
            : mode === "live"
              ? "Figures you enter are sent to the local engine; the Overview uses an invented profile."
              : "Nothing is shown until the configuration is fixed."}
        </p>
      </footer>
    </>
  );
}
