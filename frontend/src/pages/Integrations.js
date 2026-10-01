import { useState } from "react";
import { Copy, Check, ExternalLink, Code2, Globe2, Send } from "lucide-react";

const PUBLIC_URL = `${process.env.REACT_APP_BACKEND_URL}/capture`;
const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api/public/leads`;
const SITE = "www.hitechavl.com";

const iframeSnippet = `<!-- Hitech CRM lead form embed -->
<iframe
  src="${PUBLIC_URL}"
  title="Enquiry Form — Hitech Audio & Image LLP"
  style="width:100%;max-width:640px;height:760px;border:0;display:block;margin:0 auto;"
  loading="lazy">
</iframe>`;

const formSnippet = `<!-- Hitech CRM custom HTML form -->
<form id="hai-lead-form" style="max-width:520px;font-family:system-ui,sans-serif;">
  <input name="name" placeholder="Your name *" required style="width:100%;padding:12px;margin-bottom:10px;border:1px solid #cbd5e1;border-radius:6px;" />
  <input name="email" type="email" placeholder="Email" style="width:100%;padding:12px;margin-bottom:10px;border:1px solid #cbd5e1;border-radius:6px;" />
  <input name="phone" placeholder="Phone / WhatsApp" style="width:100%;padding:12px;margin-bottom:10px;border:1px solid #cbd5e1;border-radius:6px;" />
  <input name="company" placeholder="Company" style="width:100%;padding:12px;margin-bottom:10px;border:1px solid #cbd5e1;border-radius:6px;" />
  <input name="interested_in" placeholder="What are you looking for?" style="width:100%;padding:12px;margin-bottom:10px;border:1px solid #cbd5e1;border-radius:6px;" />
  <textarea name="notes" placeholder="Additional details" rows="3" style="width:100%;padding:12px;margin-bottom:10px;border:1px solid #cbd5e1;border-radius:6px;"></textarea>
  <button type="submit" style="width:100%;padding:14px;background:#DC2626;color:#fff;border:0;border-radius:6px;font-weight:600;cursor:pointer;">Submit Enquiry</button>
  <p id="hai-msg" style="margin-top:10px;font-size:14px;"></p>
</form>
<script>
  document.getElementById('hai-lead-form').addEventListener('submit', async function(e) {
    e.preventDefault();
    const f = e.target, data = Object.fromEntries(new FormData(f));
    if (!data.email) delete data.email;
    data.source = 'website';
    data.source_url = window.location.href;   // auto-track which page
    const msg = document.getElementById('hai-msg');
    msg.textContent = 'Sending…';
    try {
      const r = await fetch('${API_URL}', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      if (!r.ok) throw new Error('Failed');
      msg.style.color = '#16a34a';
      msg.textContent = 'Thanks! We will be in touch within 24 hours.';
      f.reset();
    } catch(err) {
      msg.style.color = '#dc2626';
      msg.textContent = 'Could not submit. Please try again or call us.';
    }
  });
</script>`;

const widgetSnippet = `<!-- Hitech CRM floating widget — drop on any page -->
<script>
(function(){
  var API='${API_URL}';
  var b=document.createElement('button');
  b.textContent='💬 Get a Quote';
  b.style.cssText='position:fixed;bottom:24px;right:24px;z-index:9999;background:#DC2626;color:#fff;border:0;padding:14px 22px;border-radius:999px;font:600 14px system-ui,sans-serif;cursor:pointer;box-shadow:0 6px 22px rgba(220,38,38,.35);';
  b.onmouseover=function(){b.style.transform='translateY(-2px)'};
  b.onmouseout=function(){b.style.transform=''};
  b.onclick=function(){m.style.display='flex'};
  document.body.appendChild(b);
  var m=document.createElement('div');
  m.style.cssText='display:none;position:fixed;inset:0;background:rgba(15,23,42,.55);backdrop-filter:blur(4px);z-index:10000;align-items:center;justify-content:center;font:14px system-ui,sans-serif;';
  m.innerHTML='<div style="background:#fff;border-radius:12px;max-width:480px;width:92%;padding:28px;position:relative;">'+
    '<button id="hai-x" style="position:absolute;top:12px;right:12px;background:none;border:0;font-size:22px;cursor:pointer;color:#64748B;">×</button>'+
    '<div style="font:800 22px system-ui;letter-spacing:-.02em;color:#0F172A;margin-bottom:6px;">Tell us what you need</div>'+
    '<div style="color:#64748B;font-size:13px;margin-bottom:16px;">Pro audio · broadcast · imaging — imported direct from OEMs.</div>'+
    '<form id="hai-f">'+
    '<input name="name" placeholder="Your name *" required style="width:100%;padding:11px;margin-bottom:8px;border:1px solid #cbd5e1;border-radius:6px;"/>'+
    '<input name="email" type="email" placeholder="Email" style="width:100%;padding:11px;margin-bottom:8px;border:1px solid #cbd5e1;border-radius:6px;"/>'+
    '<input name="phone" placeholder="Phone / WhatsApp" style="width:100%;padding:11px;margin-bottom:8px;border:1px solid #cbd5e1;border-radius:6px;"/>'+
    '<input name="company" placeholder="Company" style="width:100%;padding:11px;margin-bottom:8px;border:1px solid #cbd5e1;border-radius:6px;"/>'+
    '<input name="interested_in" placeholder="What are you looking for?" style="width:100%;padding:11px;margin-bottom:8px;border:1px solid #cbd5e1;border-radius:6px;"/>'+
    '<button type="submit" style="width:100%;padding:12px;background:#DC2626;color:#fff;border:0;border-radius:6px;font-weight:600;cursor:pointer;">Submit</button>'+
    '<p id="hai-r" style="margin-top:10px;font-size:13px;text-align:center;"></p></form></div>';
  document.body.appendChild(m);
  m.querySelector('#hai-x').onclick=function(){m.style.display='none'};
  m.onclick=function(e){if(e.target===m)m.style.display='none'};
  m.querySelector('#hai-f').addEventListener('submit',async function(e){
    e.preventDefault();
    var d=Object.fromEntries(new FormData(e.target));
    if(!d.email)delete d.email;
    d.source='website';d.source_url=window.location.href;
    var r=m.querySelector('#hai-r');r.textContent='Sending…';
    try{
      var x=await fetch(API,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)});
      if(!x.ok)throw 0;
      r.style.color='#16a34a';r.textContent='Thanks — we will be in touch shortly.';
      e.target.reset();
      setTimeout(function(){m.style.display='none';r.textContent=''},2200);
    }catch(e2){r.style.color='#dc2626';r.textContent='Could not submit. Please try again.';}
  });
})();
</script>`;

const curlSnippet = `curl -X POST "${API_URL}" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "Prospect name",
    "email": "buyer@example.com",
    "phone": "+91 98xxxxxx",
    "company": "Acme Events Pvt Ltd",
    "interested_in": "L-Acoustics K2 for 1000-pax venue",
    "notes": "Looking for full PA system"
  }'`;

export default function Integrations() {
  return (
    <div className="p-8 max-w-[1200px] mx-auto" data-testid="integrations-page">
      <header className="mb-8">
        <div className="label-eyebrow mb-2">Integrations</div>
        <h1 className="font-display text-4xl font-bold tracking-tighter text-slate-900">Connect {SITE}</h1>
        <p className="text-sm text-slate-600 mt-2 max-w-2xl">
          Three ways to pipe leads from your website straight into this CRM. Every submission auto-assigns
          to a sales rep and shows up under <span className="font-semibold">Source: Website</span>.
        </p>
      </header>

      {/* Option 1: Floating Widget — easiest */}
      <Section
        num="01"
        title="Floating widget (recommended — easiest)"
        subtitle={`Paste this one <script> just before </body> on ${SITE}. A red "Get a Quote" button floats in the bottom-right of every page; clicking it opens a branded enquiry modal. Submissions land here automatically with the originating page URL.`}
        icon={Code2}
      >
        <CodeBlock code={widgetSnippet} testid="copy-widget" />
      </Section>

      {/* Option 2: Direct link */}
      <Section
        num="02"
        title="Direct link button"
        subtitle={`Add a "Get a Quote" button anywhere on ${SITE} that opens this hosted form in a new tab.`}
        icon={Globe2}
      >
        <div className="flex items-center gap-3 bg-slate-50 border border-slate-200 rounded-md p-3 mb-3">
          <code className="flex-1 text-sm text-slate-800 font-mono break-all">{PUBLIC_URL}</code>
          <CopyBtn value={PUBLIC_URL} testid="copy-public-url" />
          <a
            href={PUBLIC_URL}
            target="_blank"
            rel="noreferrer"
            className="text-slate-700 hover:text-slate-900 p-1.5"
            title="Open in new tab"
            data-testid="open-public-url"
          >
            <ExternalLink className="w-4 h-4" />
          </a>
        </div>
        <CodeBlock title="HTML button" code={`<a href="${PUBLIC_URL}" target="_blank"
   style="display:inline-block;padding:14px 28px;background:#0f172a;color:#fff;text-decoration:none;border-radius:6px;font-weight:600;">
  Get a Quote →
</a>`} testid="copy-link-html" />
      </Section>

      {/* Option 3: Iframe embed */}
      <Section
        num="03"
        title="Iframe embed (zero code on your end)"
        subtitle="Paste this anywhere on your contact / enquiry page. The form is fully hosted and styled to match the CRM."
        icon={Code2}
      >
        <CodeBlock code={iframeSnippet} testid="copy-iframe" />
      </Section>

      {/* Option 4: Native form */}
      <Section
        num="04"
        title="Native HTML form (full control over styling)"
        subtitle="Drop this directly into your Wordpress / static page. It posts straight to the CRM API — no iframe, no branding."
        icon={Code2}
      >
        <CodeBlock code={formSnippet} testid="copy-form" />
      </Section>

      {/* Option 5: API */}
      <Section
        num="05"
        title="Direct API (for developers / Zapier / Make)"
        subtitle="POST to this endpoint with JSON. No auth required. Use this from any backend, automation tool, or chatbot."
        icon={Code2}
      >
        <div className="flex items-center gap-3 bg-slate-50 border border-slate-200 rounded-md p-3 mb-3">
          <span className="text-xs font-bold text-green-700 bg-green-100 px-2 py-1 rounded-sm">POST</span>
          <code className="flex-1 text-sm text-slate-800 font-mono break-all">{API_URL}</code>
          <CopyBtn value={API_URL} testid="copy-api-url" />
        </div>
        <CodeBlock title="cURL example" code={curlSnippet} testid="copy-curl" />

        <div className="mt-4 grid grid-cols-2 md:grid-cols-3 gap-2 text-xs">
          {[
            ["name", "Required"],
            ["email", "Optional"],
            ["phone", "Optional"],
            ["company", "Optional"],
            ["interested_in", "Optional"],
            ["notes", "Optional"],
          ].map(([f, r]) => (
            <div key={f} className="border border-slate-200 rounded-md px-3 py-2">
              <div className="font-mono text-slate-900 font-semibold">{f}</div>
              <div className="text-slate-500">{r}</div>
            </div>
          ))}
        </div>
      </Section>

      <div className="bg-slate-900 text-white rounded-md p-6 mt-6">
        <div className="label-eyebrow !text-white/70 mb-2">Heads up</div>
        <p className="text-sm text-white/90 leading-relaxed">
          All five methods land in <span className="font-semibold">/leads</span> under{" "}
          <span className="font-semibold">Source: Website</span> and trigger auto-assignment to a sales rep.
          The originating page URL is captured automatically (visible on each lead as{" "}
          <span className="font-mono text-xs bg-white/10 px-1.5 py-0.5 rounded">source_url</span>).
          Once {SITE} is live with the embed, leads flow in automatically — no further setup needed.
        </p>
      </div>

      <LiveTest />
    </div>
  );
}

function Section({ num, title, subtitle, icon: Icon, children }) {
  return (
    <div className="bg-white border border-slate-200 rounded-md p-6 mb-4">
      <div className="flex items-start gap-4 mb-5">
        <div className="font-display text-3xl font-black tracking-tighter text-slate-300">{num}</div>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <Icon className="w-4 h-4 text-slate-500" />
            <h2 className="font-display text-xl font-bold text-slate-900">{title}</h2>
          </div>
          <p className="text-sm text-slate-600">{subtitle}</p>
        </div>
      </div>
      {children}
    </div>
  );
}

function CodeBlock({ code, title, testid }) {
  return (
    <div className="relative">
      {title && <div className="label-eyebrow mb-2">{title}</div>}
      <pre className="bg-slate-950 text-slate-100 text-xs leading-relaxed p-4 rounded-md overflow-x-auto font-mono">{code}</pre>
      <div className="absolute top-2 right-2">
        <CopyBtn value={code} testid={testid} dark />
      </div>
    </div>
  );
}

function CopyBtn({ value, dark = false, testid }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value);
    } catch {
      const t = document.createElement("textarea");
      t.value = value;
      document.body.appendChild(t);
      t.select();
      document.execCommand("copy");
      document.body.removeChild(t);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };
  return (
    <button
      onClick={copy}
      data-testid={testid}
      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-colors ${
        dark ? "bg-slate-800 text-white hover:bg-slate-700" : "bg-slate-900 text-white hover:bg-slate-800"
      }`}
    >
      {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

function LiveTest() {
  const [name, setName] = useState("Test Lead");
  const [email, setEmail] = useState("test@hitechavl.com");
  const [phone, setPhone] = useState("+91 9999999999");
  const [interested, setInterested] = useState("L-Acoustics demo request");
  const [status, setStatus] = useState(null); // null | "loading" | "ok" | "err"
  const [leadId, setLeadId] = useState(null);
  const [err, setErr] = useState("");

  const send = async () => {
    setStatus("loading");
    setErr("");
    setLeadId(null);
    try {
      const r = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          email: email || undefined,
          phone,
          interested_in: interested,
          source: "website",
          source_url: window.location.href,
          notes: "Test submission from Integrations panel",
        }),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const j = await r.json();
      setStatus("ok");
      setLeadId(j.lead_id);
    } catch (e) {
      setStatus("err");
      setErr(e.message || "Submission failed");
    }
  };

  return (
    <div className="bg-white border border-slate-200 rounded-md p-6 mt-4" data-testid="live-test-panel">
      <div className="flex items-start gap-4 mb-5">
        <div className="font-display text-3xl font-black tracking-tighter text-slate-300">06</div>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <Send className="w-4 h-4 text-slate-500" />
            <h2 className="font-display text-xl font-bold text-slate-900">Test the connection</h2>
          </div>
          <p className="text-sm text-slate-600">
            Fires a sample submission against{" "}
            <code className="font-mono text-xs bg-slate-100 px-1.5 py-0.5 rounded">/api/public/leads</code>{" "}
            so you can confirm the pipeline before pasting the embed into {SITE}.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
        <input
          data-testid="live-test-name"
          className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Name"
        />
        <input
          data-testid="live-test-email"
          className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="Email (optional)"
        />
        <input
          data-testid="live-test-phone"
          className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          placeholder="Phone"
        />
        <input
          data-testid="live-test-interested"
          className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm"
          value={interested}
          onChange={(e) => setInterested(e.target.value)}
          placeholder="Interested in"
        />
      </div>

      <button
        data-testid="live-test-submit"
        onClick={send}
        disabled={status === "loading" || !name.trim()}
        className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white text-sm font-semibold rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <Send className="w-4 h-4" />
        {status === "loading" ? "Sending…" : "Send test lead"}
      </button>

      {status === "ok" && (
        <div
          data-testid="live-test-success"
          className="mt-4 bg-green-50 border border-green-200 text-green-800 rounded-md px-4 py-3 text-sm"
        >
          ✓ Lead created. ID:{" "}
          <span className="font-mono">{leadId}</span> — open the{" "}
          <a href="/leads" className="font-semibold underline">
            Leads page
          </a>{" "}
          to see it.
        </div>
      )}
      {status === "err" && (
        <div
          data-testid="live-test-error"
          className="mt-4 bg-red-50 border border-red-200 text-red-800 rounded-md px-4 py-3 text-sm"
        >
          ✗ Failed: {err}
        </div>
      )}
    </div>
  );
}

