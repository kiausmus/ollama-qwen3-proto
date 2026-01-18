
Session
    - id (primary key)
    - name (string)
    - created_at (datetime)
    - updated_at (datetime)

ChatLog
    - id (primary key)
    - session_id (foreign key to Session.id)
    - message (text)
    - created_at (datetime)
    - updated_at (datetime)