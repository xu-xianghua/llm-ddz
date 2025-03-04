const Protocol = {
    CLI_CHEAT : 1,
    SER_CHEAT : 2,

    CLI_LOGIN : 11,
    SER_LOGIN : 12,

    CLI_LIST_TABLE : 15,
    SER_LIST_TABLE : 16,

    CLI_CREATE_TABLE : 17,
    SER_CREATE_TABLE : 18,

    CLI_JOIN_TABLE : 19,
    SER_JOIN_TABLE : 20,

    CLI_DEAL_POKER : 31,
    SER_DEAL_POKER : 32,

    CLI_CALL_SCORE : 33,
    SER_CALL_SCORE : 34,

    CLI_HOLE_POKER : 35,
    SER_HOLE_POKER : 36,

    CLI_SHOT_POKER : 37,
    SER_SHOT_POKER : 38,

    CLI_GAME_OVER : 41,
    SER_GAME_OVER : 42,

    CLI_CHAT : 43,
    SER_CHAT : 44,

    CLI_RESTART : 45,
    SER_RESTART : 46
};

// 使用本地模拟模式
const USE_LOCAL_SIMULATION = true;

class Socket {
    constructor() {
        this.websocket = null;
        this.connected = false;
        this.messageHandler = null;
        this.openHandler = null;
        this.errorHandler = null;
    }

    connect(onopen, onmessage, onerror) {
        if (USE_LOCAL_SIMULATION) {
            // 本地模拟模式
            this.openHandler = onopen;
            this.messageHandler = onmessage;
            this.errorHandler = onerror;
            
            // 模拟连接成功
            console.log("LOCAL SIMULATION: CONNECTED");
            this.connected = true;
            
            // 调用连接成功回调
            if (this.openHandler) {
                setTimeout(() => this.openHandler(), 100);
            }
            return;
        }

        // 真实网络模式
        if (this.websocket != null) {
            return;
        }

        const protocol = window.location.protocol.startsWith('https') ? 'wss://' : 'ws://';
        const host = window.location.host;
        this.websocket = new WebSocket(protocol + host + "/ws");
        this.websocket.binaryType = 'arraybuffer';
        this.websocket.onopen = function (evt) {
            console.log("CONNECTED");
            onopen();
        };

        this.websocket.onerror = function (evt) {
            console.log('CONNECT ERROR: ' + evt.data);
            this.websocket = null;
            onerror();
        };

        this.websocket.onclose = function (evt) {
            console.log("DISCONNECTED");
            this.websocket = null;
        };

        this.websocket.onmessage = function (evt) {
            console.log('RECV: ' + evt.data);
            onmessage(JSON.parse(evt.data));
        };
    }

    send(msg) {
        if (USE_LOCAL_SIMULATION) {
            // 本地模拟模式
            console.log('LOCAL SIMULATION - SEND: ' + JSON.stringify(msg));
            
            // 模拟服务器响应
            this.simulateResponse(msg);
            return;
        }

        // 真实网络模式
        console.log('SEND: ' + JSON.stringify(msg));
        this.websocket.send(JSON.stringify(msg));
    }
    
    // 模拟服务器响应
    simulateResponse(msg) {
        if (!this.messageHandler) return;
        
        // 解析消息类型和数据
        const [type, data] = msg;
        
        // 根据不同的消息类型，模拟不同的响应
        switch (type) {
            case Protocol.CLI_LOGIN:
                // 模拟登录响应
                setTimeout(() => {
                    this.messageHandler([Protocol.SER_LOGIN, {
                        uid: 1,
                        name: data.name || "本地玩家",
                        point: 1000
                    }]);
                }, 200);
                break;
                
            case Protocol.CLI_LIST_TABLE:
                // 模拟房间列表响应
                setTimeout(() => {
                    this.messageHandler([Protocol.SER_LIST_TABLE, {
                        tables: [
                            { id: 1, name: "人机对战", players: 1, max: 3 }
                        ]
                    }]);
                }, 200);
                break;
                
            case Protocol.CLI_JOIN_TABLE:
                // 模拟加入房间响应
                setTimeout(() => {
                    this.messageHandler([Protocol.SER_JOIN_TABLE, {
                        table_id: data.table_id,
                        seat: 0,
                        players: [
                            { uid: 1, name: window.playerInfo.name, seat: 0 },
                            { uid: 2, name: "电脑玩家1", seat: 1 },
                            { uid: 3, name: "电脑玩家2", seat: 2 }
                        ]
                    }]);
                }, 200);
                break;
                
            // 可以根据需要添加更多的模拟响应
            case Protocol.CLI_DEAL_POKER:
                // 模拟发牌响应
                setTimeout(() => {
                    this.messageHandler([Protocol.SER_DEAL_POKER, {
                        pokers: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17]
                    }]);
                }, 200);
                break;
                
            case Protocol.CLI_CALL_SCORE:
                // 模拟叫分响应
                setTimeout(() => {
                    this.messageHandler([Protocol.SER_CALL_SCORE, {
                        uid: 1,
                        score: data.score,
                        turn: 2
                    }]);
                }, 200);
                break;
                
            default:
                console.log("未处理的消息类型:", type);
                break;
        }
    }
}

export {Protocol, Socket}