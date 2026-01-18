const { useEffect, useRef, useState } = React;
const h = React.createElement;

function App() {
  const [messages, setMessages] = useState([
    { role: "system", content: "You are a helpful assistant." }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  // 보고서 패널 상태
  const [panelOpen, setPanelOpen] = useState(false);
  const [reportContent, setReportContent] = useState("");
  const [reportLoading, setReportLoading] = useState(false);

  const chatRef = useRef(null);
  const sendingRef = useRef(false);
  const sessionIdRef = useRef(null);

  if (!sessionIdRef.current) {
    if (window.crypto && typeof window.crypto.randomUUID === "function") {
      sessionIdRef.current = window.crypto.randomUUID();
    } else {
      sessionIdRef.current = `s-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    }
  }

  useEffect(() => {
    if (!chatRef.current) return;
    requestAnimationFrame(() => {
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
    });
  }, [messages, loading]);

  const pushAssistant = (text) => {
    setMessages((prev) => prev.concat({ role: "assistant", content: text }));
  };

  const send = async () => {
    const text = input.trim();
    if (!text) return;

    if (sendingRef.current) return;
    sendingRef.current = true;

    const next = messages.concat({ role: "user", content: text });
    setMessages(next);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: next, session_id: sessionIdRef.current })
      });

      if (!res.ok) {
        let detail = "";
        try {
          const j = await res.json();
          detail = j?.detail ? String(j.detail) : JSON.stringify(j);
        } catch {
          detail = await res.text();
        }
        throw new Error(detail || `HTTP ${res.status}`);
      }

      const data = await res.json();
      pushAssistant(data?.content ?? "");
    } catch (e) {
      pushAssistant("에러: " + (e?.message || String(e)));
    } finally {
      setLoading(false);
      sendingRef.current = false;
    }
  };

  const onKeyDown = (e) => {
    const isCmdOrCtrlEnter = (e.key === "Enter") && (e.metaKey || e.ctrlKey);
    if ((e.key === "Enter" && !e.shiftKey) || isCmdOrCtrlEnter) {
      e.preventDefault();
      send();
    }
  };

  const reset = () => {
    setMessages([{ role: "system", content: "You are a helpful assistant." }]);
    setInput("");
    setLoading(false);
    sendingRef.current = false;
  };

  const closeReportPanel = () => {
    setPanelOpen(false);
  };

  const requestReport = async () => {
    if (reportLoading) return;
    

    setPanelOpen(true);
    setReportLoading(true);
    setReportContent("");
    try {
      const res = await fetch("/api/agent/stock-report", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          symbol: symbol.trim(),
          session_id: sessionIdRef.current
        })
      });

      if (!res.ok) {
        let detail = "";
        try {
          const j = await res.json();
          detail = j?.detail ? String(j.detail) : JSON.stringify(j);
        } catch {
          detail = await res.text();
        }
        throw new Error(detail || `HTTP ${res.status}`);
      }

      const data = await res.json();
      const report = data?.report ?? "";
      setReportContent(report || "보고서 응답이 비어 있습니다.");
    } catch (e) {
      setReportContent("에러: " + (e?.message || String(e)));
    } finally {
      setReportLoading(false);
    }
  };

  return h("div", null,
    h("div", { className: "top-actions" },
      h("button", { className: "smallbtn", onClick: requestReport }, "보고서 보기")
    ),
    h("div", { className: "chat", ref: chatRef },
      messages.map((m, i) =>
        h("div", { className: "msg", key: i },
          h("div", { className: "role" }, m.role),
          h("div", { className: "content" }, m.content)
        )
      ),
      loading ? h("div", { className: "msg" },
        h("div", { className: "role" }, "assistant"),
        h("div", { className: "content" }, "생각중...")
      ) : null
    ),

    h("div", { className: "composer" },
      h("textarea", {
        value: input,
        onChange: (e) => setInput(e.target.value),
        onKeyDown,
        placeholder: "질문 입력…",
        autoFocus: true
      }),
      h("button", { onClick: send, disabled: !input.trim() || loading },
        loading ? "처리중" : "전송"
      )
    ),

    h("div", { className: "row" },
      h("button", { className: "smallbtn", onClick: reset }, "대화 초기화")
    ),

    // 슬라이드 패널
    h("div", { className: "slide-panel" + (panelOpen ? " open" : "") },
      h("div", { className: "panel-header" },
        h("h3", null, "종목 보고서"),
        h("button", { className: "panel-close", onClick: closeReportPanel }, "×")
      ),
      h("div", { className: "panel-body" },
        reportLoading
          ? "보고서를 생성하고 있습니다..."
          : reportContent
            ? reportContent
            : h("div", { className: "panel-placeholder" }, "보고서가 없습니다.")
      )
    )
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(h(App));
