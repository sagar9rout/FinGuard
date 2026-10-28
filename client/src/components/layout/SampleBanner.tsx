export type BannerMode = "mock" | "live" | "misconfigured";

interface Props {
  readonly mode: BannerMode;
  readonly apiOrigin?: string;
}

/** Persistent, always-visible disclosure of which engine this page is wired to. Rendered once by the app shell. */
export function SampleBanner({ mode, apiOrigin }: Props) {
  if (mode === "live") {
    return (
      <div className="sample-banner" role="note" aria-label="Local engine notice">
        <strong>LOCAL ENGINE · PROTOTYPE</strong>
        <span className="sample-banner__detail">
          Requests go to the FinGuard engine on this computer ({apiOrigin}). The Overview uses an invented profile. There is no
          sign-in and this is not a production system.
        </span>
      </div>
    );
  }
  if (mode === "misconfigured") {
    return (
      <div className="sample-banner" role="note" aria-label="Configuration notice">
        <strong>NOT CONNECTED · CONFIGURATION ERROR</strong>
        <span className="sample-banner__detail">No engine is being called and no figures are shown.</span>
      </div>
    );
  }
  return (
    <div className="sample-banner" role="note" aria-label="Sample data notice">
      <strong>SAMPLE DATA · MOCK ENGINE</strong>
      <span className="sample-banner__detail">
        Invented figures and committed sample results. No real account is read and no live engine is called.
      </span>
    </div>
  );
}
