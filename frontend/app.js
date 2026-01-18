const { useEffect, useRef, useState, useCallback } = React;
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

  // 세션 목록 상태
  const [sessions, setSessions] = useState([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [currentSessionId, setCurrentSessionId] = useState(null);

  const chatRef = useRef(null);
  const sendingRef = useRef(false);
  const sessionIdRef = useRef(null);
  const lastReportMessageCountRef = useRef(null);
  const lastReportContentRef = useRef("");

  const generateSessionId = () => {
    if (window.crypto && typeof window.crypto.randomUUID === "function") {
      return window.crypto.randomUUID();
    }
    return `s-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  };

  if (!sessionIdRef.current) {
    sessionIdRef.current = generateSessionId();
    setCurrentSessionId(sessionIdRef.current);
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
      refreshSessionsAfterSend();
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

  // 세션 목록 가져오기
  const fetchSessions = useCallback(async () => {
    setSessionsLoading(true);
    try {
      const res = await fetch("/api/ssessions");
      if (!res.ok) throw new Error("세션 목록을 가져올 수 없습니다.");
      const data = await res.json();
      setSessions(data.sessions || []);
    } catch (e) {
      console.error("세션 목록 조회 실패:", e);
    } finally {
      setSessionsLoading(false);
    }
  }, []);

  // 세션 선택시 메시지 로드
  const selectSession = async (sessionId) => {
    if (sessionId === sessionIdRef.current) return;

    setLoading(true);
    try {
      const res = await fetch(`/api/sessions/${sessionId}/messages`);
      if (!res.ok) throw new Error("메시지를 가져올 수 없습니다.");
      const data = await res.json();
      setMessages(data.messages || [{ role: "system", content: "You are a helpful assistant." }]);
      sessionIdRef.current = sessionId;
      setCurrentSessionId(sessionId);
      lastReportMessageCountRef.current = null;
      lastReportContentRef.current = "";
      setReportContent("");
    } catch (e) {
      console.error("세션 메시지 로드 실패:", e);
    } finally {
      setLoading(false);
    }
  };

  // 새 대화 시작
  const startNewChat = () => {
    window.location.href = "/chat";
  };

  // 초기 세션 목록 로드
  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  // 메시지 전송 후 세션 목록 갱신
  const refreshSessionsAfterSend = () => {
    setTimeout(() => fetchSessions(), 500);
  };

  const closeReportPanel = () => {
    setPanelOpen(false);
  };

  const handleInputFocus = () => {
    setPanelOpen(false);
  };

  const requestReport = async () => {
    if (!sessionIdRef.current) {
      alert("대화를 먼저 시작해주세요.");
      return;
    }
    if (reportLoading) return;

    const currentMessageCount = messages.length;
   
    setPanelOpen(true);

    
    setReportLoading(true);
    if (lastReportContentRef.current) {
      setReportContent(lastReportContentRef.current);
    } else {
      setReportContent("");
    }
    try {
      const tryGetReport = async () => {
        const res = await fetch(`/api/sessions/${sessionIdRef.current}/report`);
        if (res.status === 404) {
          return null;
        }
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
        return await res.json();
      };

      const createReport = async () => {
        const res = await fetch("/api/agent/stock-report", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
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

        return await res.json();
      };

      const existing = await tryGetReport();
      const report = existing?.report ?? "";
      if (report) {
        setReportContent(report);
        lastReportMessageCountRef.current = currentMessageCount;
        lastReportContentRef.current = report;
      } else {
        const created = await createReport();
        const createdReport = created?.report ?? "";
        setReportContent(createdReport || "보고서 응답이 비어 있습니다.");
        lastReportMessageCountRef.current = currentMessageCount;
        lastReportContentRef.current = createdReport || "보고서 응답이 비어 있습니다.";
      }
    } catch (e) {
      setReportContent("에러: " + (e?.message || String(e)));
    } finally {
      setReportLoading(false);
    }
  };

  return h("div", null,
    h("div", { className: "main-layout" },
      // 왼쪽: 세션 목록
      h("div", { className: "session-list" },
        h("div", { className: "session-title" }, "대화 목록"),
        h("button", {
          className: "smallbtn new-chat-btn",
          onClick: startNewChat,
          style: { marginBottom: "10px", width: "100%" }
        }, "+ 새 대화"),
        h("div", { className: "session-items" },
          sessionsLoading
            ? h("div", { className: "session-loading" }, "로딩 중...")
            : sessions.length === 0
              ? h("div", { className: "session-empty" }, "저장된 대화가 없습니다.")
              : sessions.map((s) =>
                  h("button", {
                    key: s.id,
                    className: "session-item" + (s.id === currentSessionId ? " active" : ""),
                    onClick: () => selectSession(s.id),
                    title: s.name
                  }, s.name || "대화")
                )
        )
      ),

      // 오른쪽: 채팅 영역
      h("div", { className: "chat-area" + (panelOpen ? " panel-open" : "") },
      h("div", { className: "top-actions" },
        h("button", {
          className: "smallbtn",
          onClick: () => { window.location.href = "/"; }
        }, "대시보드"),
        h("button", {
          className: "smallbtn",
          onClick: requestReport,
          disabled: !sessionIdRef.current || messages.length === 0
          }, "보고서 보기")
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
            onFocus: handleInputFocus,
            placeholder: "질문 입력…",
            autoFocus: true
          }),
          h("button", { onClick: send, disabled: !input.trim() || loading },
            loading ? "처리중" : "전송"
          )
        ),

        h("div", { className: "row" },
          h("button", { className: "smallbtn", onClick: reset }, "대화 초기화")
        )
      )
    ),

    // 슬라이드 패널
    h("div", { className: "slide-panel" + (panelOpen ? " open" : "") },
      h("div", { className: "panel-header" },
        h("h3", null, "종목 보고서"),
        h("button", { className: "panel-close", onClick: closeReportPanel }, "×")
      ),
      h("div", { className: "panel-body" },
        reportLoading
          ? h("div", { className: "panel-loading" },
              h("div", { className: "spinner", "aria-hidden": "true" }),
              h("div", { className: "panel-loading-text" }, "보고서를 생성하고 있습니다...")
            )
          : reportContent
            ? reportContent
            : h("div", { className: "panel-placeholder" }, "보고서가 없습니다.")
      )
    )
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(h(App));
