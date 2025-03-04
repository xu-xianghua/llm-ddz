import {Poker, Rule} from '/static/js/rule.mjs'
import {Player, createPlay} from '/static/js/player.mjs'
import {Protocol, Socket} from '/static/js/net.mjs'

class Observer {

    constructor() {
        this.state = {};
        this.subscribers = {};
    }

    get(key) {
        return this.state[key];
    }

    set(key, val) {
        // 忽略countdown相关的更新，彻底禁用倒计时
        if (key === 'countdown') {
            return;
        }
        
        const keys = key.split('.');
        if (keys.length === 1) {
            this.state[key] = val;
        } else {
            this.state[keys[0]][keys[1]] = val;
            key = keys[0];
        }
        const newVal = this.state[key];
        const subscribers = this.subscribers;
        if (subscribers.hasOwnProperty(key)) {
            subscribers[key].forEach(function (cb) {
                if (cb) cb(newVal);
            });
        }
    }

    subscribe(key, cb) {
        // 对于countdown订阅，提供一个空函数，不执行任何操作
        if (key === 'countdown') {
            return;
        }
        
        const subscribers = this.subscribers;
        if (subscribers.hasOwnProperty(key)) {
            subscribers[key].push(cb);
        } else {
            subscribers[key] = [cb];
        }
    }

    unsubscribe(key, cb) {
        const subscribers = this.subscribers;
        if (subscribers.hasOwnProperty(key)) {
            const index = subscribers.indexOf(cb);
            if (index > -1) {
                subscribers.splice(index, 1);
            }
        }
    }
}

const observer = new Observer();

export class Game {
    constructor(game) {
        this.players = [];

        this.tablePoker = [];
        this.tablePokerPic = {};

        this.lastShotPlayer = null;

        this.whoseTurn = 0;
    }

    init(baseScore) {
        observer.set('baseScore', baseScore);
    }

    create() {
        Rule.RuleList = this.cache.getJSON('rule');
        this.stage.backgroundColor = '#182d3b';

        // 初始化背景音乐
        this.backgroundMusic = this.game.add.audio('music_game');
        this.backgroundMusic.loop = true;
        
        // 根据设置决定是否播放音乐
        const musicEnabled = localStorage.getItem('musicEnabled') === 'true';
        if (musicEnabled && !this.game.sound.mute) {
            this.backgroundMusic.play();
        }

        this.players.push(createPlay(0, this));
        this.players.push(createPlay(1, this));
        this.players.push(createPlay(2, this));
        this.players[0].updateInfo(window.playerInfo.uid, window.playerInfo.name);
        const protocol = location.protocol.startsWith("https") ? "wss://" : "ws://";
        this.socket = new Socket(protocol + location.host + "/ws");
        this.socket.connect(this.onopen.bind(this), this.onmessage.bind(this), this.onerror.bind(this));

        const width = this.game.world.width;
        const height = this.game.world.height;

        const titleBar = this.game.add.text(width / 2, 0, `房间号:${0} 底分: 0 倍数: 0`, {
            font: "22px",
            fill: "#fff",
            align: "center"
        });
        titleBar.anchor.set(0.5, 0);
        observer.subscribe('room', function (room) {
            titleBar.text = `房间号:${room.id} 底分: ${room.origin} 倍数: ${room.multiple}`;
        });

        // 创建准备按钮
        const that = this;
        
        const ready = this.game.make.button(width / 2, height * 0.6, "btn", function () {
            this.send_message([Protocol.REQ_READY, {"ready": 1}]);
        }, this, 'ready.png', 'ready.png', 'ready.png');
        ready.anchor.set(0.5, 0);
        this.game.world.add(ready);

        observer.subscribe('ready', function (is_ready) {
            ready.visible = !is_ready;
        });

        // 创建抢地主按钮
        const group = this.game.add.group();
        let pass = this.game.make.button(width * 0.4, height * 0.6, "btn", function () {
            this.game.add.audio('f_score_0').play();
            this.send_message([Protocol.REQ_CALL_SCORE, {"rob": 0}]);
        }, this, 'score_0.png', 'score_0.png', 'score_0.png');
        pass.anchor.set(0.5, 0);
        group.add(pass);

        const rob = this.game.make.button(width * 0.6, height * 0.6, "btn", function () {
            this.game.add.audio('f_score_1').play();
            this.send_message([Protocol.REQ_CALL_SCORE, {"rob": 1}]);
        }, this, 'score_1.png', 'score_1.png', 'score_1.png');
        rob.anchor.set(0.5, 0);
        group.add(rob);
        group.visible = false;

        observer.subscribe('rob', function (is_rob) {
            group.visible = is_rob;
        });
    }

    onopen() {
        console.log('socket onopen');
        this.socket.send([Protocol.REQ_ROOM_LIST, {}]);
        this.socket.send([Protocol.REQ_JOIN_ROOM, {"room": -1, "level": observer.get('baseScore')}]);
    }

    onerror() {
        console.log('socket onerror, try reconnect.');
        this.socket.connect(this.onopen.bind(this), this.onmessage.bind(this), this.onerror.bind(this));
    }

    send_message(request) {
        this.socket.send(request);
    }

    onmessage(message) {
        const code = message[0], packet = message[1];
        console.log("收到消息:", code, packet);
        switch (code) {
            case Protocol.RSP_ROOM_LIST:
                console.log(code, packet);
                break;
            case Protocol.RSP_JOIN_ROOM:
                observer.set('room', packet['room']);
                const syncInfo = packet['players'];
                for (let i = 0; i < syncInfo.length; i++) {
                    if (syncInfo[i].uid === this.players[0].uid) {
                        let info_1 = syncInfo[(i + 1) % 3];
                        let info_2 = syncInfo[(i + 2) % 3];
                        this.players[1].updateInfo(info_1.uid, info_1.name);
                        this.players[2].updateInfo(info_2.uid, info_2.name);
                        break;
                    }
                }
                
                // 处理房间同步中的底牌信息
                if (packet['room'] && packet['room']['bottom_cards'] && packet['room']['bottom_cards'].length === 3) {
                    console.log("从房间同步数据中获取底牌:", packet['room']['bottom_cards']);
                    this.tablePoker = packet['room']['bottom_cards'];
                    
                    // 如果已经确定了地主，显示底牌
                    if (packet['room']['landlord_uid'] !== -1 && packet['room']['state'] >= 3) {
                        console.log("房间已有地主，显示底牌");
                        this.showLastThreePoker();
                    }
                }
                break;
            case Protocol.RSP_READY:
                // TODO: 显示玩家已准备状态
                if (packet['uid'] === this.players[0].uid) {
                    observer.set('ready', true);
                }
                break;
            case Protocol.RSP_DEAL_POKER: {
                const playerId = packet['uid'];
                const pokers = packet['pokers'];
                console.log("收到发牌消息:", playerId, this.players[0].uid, pokers);
                if (playerId === this.players[0].uid) {
                    console.log("处理自己的牌");
                    this.dealPoker(pokers);
                    this.whoseTurn = this.uidToSeat(playerId);
                    this.startCallScore();
                }
                break;
            }
            case Protocol.RSP_CALL_SCORE: {
                const playerId = packet['uid'];
                const rob = packet['rob'];
                const landlord = packet['landlord'];
                this.whoseTurn = this.uidToSeat(playerId);

                const hanzi = ['不抢', "抢地主"];
                this.players[this.whoseTurn].say(hanzi[rob]);
                
                console.log("收到抢地主结果:", packet);
                console.log("当前玩家:", playerId, "抢地主决定:", rob);
                console.log("地主:", landlord, "底牌:", packet['pokers']);

                observer.set('rob', false);
                if (landlord === -1) {
                    console.log("抢地主未结束，轮到下一个玩家");
                    this.whoseTurn = (this.whoseTurn + 1) % 3;
                    this.startCallScore();
                } else {
                    console.log("抢地主结束，地主是:", landlord);
                    this.whoseTurn = this.uidToSeat(landlord);
                    console.log("地主座位号:", this.whoseTurn);
                    
                    // 确保底牌存在
                    if (packet['pokers'] && packet['pokers'].length === 3) {
                        console.log("设置底牌:", packet['pokers']);
                        this.tablePoker[0] = packet['pokers'][0];
                        this.tablePoker[1] = packet['pokers'][1];
                        this.tablePoker[2] = packet['pokers'][2];
                        
                        // 设置地主标识
                        this.players[this.whoseTurn].setLandlord();
                        console.log("显示底牌");
                        this.showLastThreePoker();
                    } else {
                        console.error("底牌不存在或长度不为3:", packet['pokers']);
                    }
                }
                observer.set('room.multiple', packet['multiple']);
                break;
            }
            case Protocol.RSP_SHOT_POKER:
                this.handleShotPoker(packet);
                observer.set('room.multiple', packet['multiple']);
                break;
            case Protocol.RSP_TURN_PLAYER: {
                console.log("收到轮到玩家出牌消息:", packet);
                const playerId = packet['uid'];
                this.whoseTurn = this.uidToSeat(playerId);
                
                // 设置上一手牌
                const lastPokers = packet['pokers'] || [];
                this.tablePoker = lastPokers;
                
                // 如果轮到玩家自己出牌
                if (this.whoseTurn === 0) {
                    console.log("轮到玩家自己出牌");
                    this.startPlay();
                }
                break;
            }
            case Protocol.RSP_GAME_OVER: {
                const winner = packet['winner'];
                const that = this;
                packet['players'].forEach(function (player) {
                    const seat = that.uidToSeat(player['uid']);
                    if (seat > 0) {
                        that.players[seat].replacePoker(player['pokers'], 0);
                        that.players[seat].reDealPoker();
                    }
                });

                this.whoseTurn = this.uidToSeat(winner);

                function gameOver() {
                    alert(that.players[that.whoseTurn].isLandlord ? "地主赢" : "农民赢");
                    observer.set('ready', false);
                    this.cleanWorld();
                }

                this.game.time.events.add(2000, gameOver, this);
                break;
            }
            // case Protocol.RSP_CHEAT:
            //     let seat = this.uidToSeat(packet[1]);
            //     this.players[seat].replacePoker(packet[2], 0);
            //     this.players[seat].reDealPoker();
            //     break;
            default:
                console.log("UNKNOWN PACKET:", packet)
        }
    }

    cleanWorld() {
        this.players.forEach(function (player) {
            player.cleanPokers();
            // player.uiLeftPoker.kill();
            player.uiHead.frameName = 'icon_farmer.png';
        });
        for (let i = 0; i < this.tablePoker.length; i++) {
            let p = this.tablePokerPic[this.tablePoker[i]];
            p.destroy();
        }
    }

    restart() {
        this.players = [];

        this.tablePoker = [];
        this.tablePokerPic = {};

        this.lastShotPlayer = null;

        this.whoseTurn = 0;

        this.stage.backgroundColor = '#182d3b';
        this.players.push(createPlay(0, this));
        this.players.push(createPlay(1, this));
        this.players.push(createPlay(2, this));
        for (let i = 0; i < 3; i++) {
            //this.players[i].uiHead.kill();
        }
    }

    update() {
    }

    uidToSeat(uid) {
        for (let i = 0; i < 3; i++) {
            if (uid === this.players[i].uid)
                return i;
        }
        console.log('ERROR uidToSeat:' + uid);
        return -1;
    }

    dealPoker(pokers) {
        console.log("开始发牌，收到的牌:", pokers);  // 添加日志输出
        // 添加一张底牌
        let p = new Poker(this, 55, 55);
        this.tablePokerPic[55] = p;
        this.game.world.add(p);

        for (let i = 0; i < 17; i++) {
            this.players[2].pokerInHand.push(55);
            this.players[1].pokerInHand.push(55);
            this.players[0].pokerInHand.push(pokers.pop());
        }

        console.log("玩家0的牌:", this.players[0].pokerInHand);  // 添加日志输出
        console.log("玩家1的牌:", this.players[1].pokerInHand);  // 添加日志输出
        console.log("玩家2的牌:", this.players[2].pokerInHand);  // 添加日志输出

        this.players[0].dealPoker();
        this.players[1].dealPoker();
        this.players[2].dealPoker();
        console.log("发牌完成");  // 添加日志输出
    }

    showLastThreePoker() {
        console.log("开始显示底牌");
        
        // 检查底牌是否存在
        if (!this.tablePoker || this.tablePoker.length !== 3) {
            console.error("底牌不存在或长度不为3:", this.tablePoker);
            return;
        }
        
        console.log("底牌:", this.tablePoker);
        
        // 删除底牌
        if (this.tablePokerPic[55]) {
            console.log("删除原底牌");
            this.tablePokerPic[55].destroy();
            delete this.tablePokerPic[55];
        } else {
            console.warn("原底牌不存在");
        }

        for (let i = 0; i < 3; i++) {
            let pokerId = this.tablePoker[i];
            console.log("创建底牌:", i, pokerId);
            let p = new Poker(this, pokerId, pokerId);
            this.tablePokerPic[pokerId] = p;
            this.game.world.add(p);
            this.game.add.tween(p).to({x: this.game.world.width / 2 + (i - 1) * 60}, 600, Phaser.Easing.Default, true);
        }
        console.log("底牌显示完成，1.5秒后发给地主");
        this.game.time.events.add(1500, this.dealLastThreePoker, this);
    }

    dealLastThreePoker() {
        console.log("开始将底牌发给地主");
        
        // 检查当前回合玩家是否是地主
        if (this.whoseTurn < 0 || this.whoseTurn >= this.players.length) {
            console.error("无效的地主座位号:", this.whoseTurn);
            return;
        }
        
        let turnPlayer = this.players[this.whoseTurn];
        console.log("地主玩家:", turnPlayer.uid, "座位号:", this.whoseTurn);
        
        // 检查底牌是否存在
        if (!this.tablePoker || this.tablePoker.length !== 3) {
            console.error("底牌不存在或长度不为3:", this.tablePoker);
            return;
        }

        for (let i = 0; i < 3; i++) {
            let pid = this.tablePoker[i];
            console.log("将底牌发给地主:", i, pid);
            let poker = this.tablePokerPic[pid];
            turnPlayer.pokerInHand.push(pid);
            turnPlayer.pushAPoker(poker);
        }
        
        console.log("地主手牌:", turnPlayer.pokerInHand);
        turnPlayer.sortPoker();
        
        if (this.whoseTurn === 0) {
            console.log("地主是玩家自己，重新排列手牌");
            turnPlayer.arrangePoker();
            const that = this;
            for (let i = 0; i < 3; i++) {
                let pid = this.tablePoker[i];
                let p = this.tablePokerPic[pid];
                let tween = this.game.add.tween(p).to({y: this.game.world.height - Poker.PH * 0.8}, 400, Phaser.Easing.Default, true);

                function adjust(p) {
                    that.game.add.tween(p).to({y: that.game.world.height - Poker.PH / 2}, 400, Phaser.Easing.Default, true, 400);
                }

                tween.onComplete.add(adjust, this, p);
            }
        } else {
            console.log("地主是AI玩家，隐藏底牌");
            let first = turnPlayer.findAPoker(55);
            for (let i = 0; i < 3; i++) {
                let pid = this.tablePoker[i];
                let p = this.tablePokerPic[pid];
                p.frame = 55 - 1;
                this.game.add.tween(p).to({x: first.x, y: first.y}, 200, Phaser.Easing.Default, true);
            }
        }

        this.tablePoker = [];
        this.lastShotPlayer = turnPlayer;
        
        console.log("底牌发放完成，开始出牌阶段");
        if (this.whoseTurn === 0) {
            console.log("地主是玩家自己，开始出牌");
            this.startPlay();
        } else {
            console.log("地主是AI玩家，等待服务器通知");
        }
    }

    handleShotPoker(packet) {
        this.whoseTurn = this.uidToSeat(packet['uid']);
        let turnPlayer = this.players[this.whoseTurn];
        let pokers = packet['pokers'];
        if (pokers.length === 0) {
            this.players[this.whoseTurn].say("不出");
        } else {
            let pokersPic = {};
            pokers.sort(Poker.comparePoker);
            let count = pokers.length;
            let gap = Math.min((this.game.world.width - Poker.PW * 2) / count, Poker.PW * 0.36);
            for (let i = 0; i < count; i++) {
                let p = turnPlayer.findAPoker(pokers[i]);
                p.id = pokers[i];
                p.frame = pokers[i] - 1;
                p.bringToTop();
                this.game.add.tween(p).to({
                    x: this.game.world.width / 2 + (i - count / 2) * gap,
                    y: this.game.world.height * 0.4
                }, 500, Phaser.Easing.Default, true);

                turnPlayer.removeAPoker(pokers[i]);
                pokersPic[p.id] = p;
            }

            for (let i = 0; i < this.tablePoker.length; i++) {
                let p = this.tablePokerPic[this.tablePoker[i]];
                // p.kill();
                p.destroy();
            }
            this.tablePoker = pokers;
            this.tablePokerPic = pokersPic;
            this.lastShotPlayer = turnPlayer;
            turnPlayer.arrangePoker();
        }
        if (turnPlayer.pokerInHand.length > 0) {
            this.whoseTurn = (this.whoseTurn + 1) % 3;
            if (this.whoseTurn === 0) {
                this.game.time.events.add(1000, this.startPlay, this);
            }
        }
    }

    startCallScore() {
        if (this.whoseTurn === 0) {
            observer.set('rob', true);
        }

    }

    startPlay() {
        console.log("开始出牌阶段");
        
        // 检查当前回合玩家
        if (this.whoseTurn < 0 || this.whoseTurn >= this.players.length) {
            console.error("无效的当前回合玩家座位号:", this.whoseTurn);
            return;
        }
        
        console.log("当前回合玩家:", this.players[this.whoseTurn].uid, "座位号:", this.whoseTurn);
        console.log("上一手牌玩家:", this.lastShotPlayer ? this.lastShotPlayer.uid : "无");
        
        if (this.isLastShotPlayer()) {
            console.log("当前玩家是上一手牌玩家，可以任意出牌");
            this.players[0].playPoker([]);
        } else {
            console.log("当前玩家不是上一手牌玩家，必须跟牌");
            console.log("上一手牌:", this.tablePoker);
            this.players[0].playPoker(this.tablePoker);
        }
    }

    finishPlay(pokers) {
        console.log("完成出牌，发送出牌请求");
        console.log("出牌:", pokers);
        this.send_message([Protocol.REQ_SHOT_POKER, {"pokers": pokers}]);
    }

    isLastShotPlayer() {
        console.log("检查当前玩家是否是上一手牌玩家");
        console.log("当前回合玩家:", this.players[this.whoseTurn].uid, "座位号:", this.whoseTurn);
        console.log("上一手牌玩家:", this.lastShotPlayer ? this.lastShotPlayer.uid : "无");
        
        const result = this.players[this.whoseTurn] === this.lastShotPlayer;
        console.log("判断结果:", result);
        return result;
    }

    quitGame() {
        this.state.start('MainMenu');
    }
}






