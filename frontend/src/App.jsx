import { useState, useRef, useEffect } from "react";
import "./App.css";

const API_URL = "http://localhost:8000";

const ROUTE_LABELS = {
  POLICY: "policy",
  ORDER_PRODUCT: "order / product",
  HYBRID: "hybrid",
  SMALL_TALK: "small talk",
  UNCLEAR: "unclear",
};

function RouteTag({ route }) {
  if (!route) return null;
  const className = `route-tag route-tag--${route.toLowerCase()}`;
  return <span className={className}>{ROUTE_LABELS[route] || route.toLowerCase()}</span>;
}

function Sources({ sources }) {
  if (!sources || sources.length === 0) return null;
  return (
    <div className="sources">
      <div className="sources__rule" />
      {sources.map((s, i) => (
        <div className="sources__row" key={i}>
          <span className="sources__name">{s.source}</span>
          <span className="sources__dist">{s.distance.toFixed(3)}</span>
        </div>
      ))}
    </div>
  );
}

function Message({ role, content, route, sources }) {
  if (role === "user") {
    return (
      <div className="message message--user">
        <div className="bubble bubble--user">{content}</div>
      </div>
    );
  }

  return (
    <div className="message message--assistant">
      <div className="bubble bubble--assistant">
        <p className="bubble__text">{content}</p>
        <div className="bubble__footer">
          <RouteTag route={route} />
        </div>
        <Sources sources={sources} />
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="message message--assistant">
      <div className="bubble bubble--assistant bubble--typing">
        <span className="dot" />
        <span className="dot" />
        <span className="dot" />
      </div>
    </div>
  );
}

export default function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function sendMessage(e) {
    e.preventDefault();
    const query = input.trim();
    if (!query || loading) return;

    setMessages((prev) => [...prev, { role: "user", content: query }]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });

      if (!res.ok) throw new Error(`Request failed (${res.status})`);

      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.answer,
          route: data.route,
          sources: data.sources,
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "Couldn't reach the assistant backend. Make sure the FastAPI server is running on localhost:8000.",
          route: null,
          sources: [],
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page">
      <header className="header">
        <div className="header__brand">
          <span className="header__mark">ShopSphere</span>
          <span className="header__tag">support desk</span>
        </div>
        <p className="header__sub">
          Ask about an order, a product, or a policy. For order questions, include the order ID.
        </p>
      </header>

      <main className="chat">
        {messages.length === 0 && (
          <div className="empty">
            <p className="empty__eyebrow">Try asking</p>
            <ul className="empty__list">
              <li>&ldquo;What is your return policy for electronics?&rdquo;</li>
              <li>&ldquo;What is the status of order e481f51cbdc54678b7cc49136f2d6af7?&rdquo;</li>
              <li>&ldquo;Can I return the product from that order?&rdquo;</li>
            </ul>
          </div>
        )}

        {messages.map((m, i) => (
          <Message key={i} {...m} />
        ))}

        {loading && <TypingIndicator />}
        <div ref={scrollRef} />
      </main>

      <form className="composer" onSubmit={sendMessage}>
        <input
          className="composer__input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="How can I help you today?"
          disabled={loading}
        />
        <button className="composer__send" type="submit" disabled={loading || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}
