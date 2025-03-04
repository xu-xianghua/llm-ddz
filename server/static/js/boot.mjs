// 支持HTTP请求和本地模拟
function get(url, payload, callback) {
    if (window.USE_LOCAL_SIMULATION) {
        // 本地模拟模式
        simulateResponse('GET', url, payload, callback);
        return;
    }
    http('GET', url, payload, callback);
}

function post(url, payload, callback) {
    if (window.USE_LOCAL_SIMULATION) {
        // 本地模拟模式
        simulateResponse('POST', url, payload, callback);
        return;
    }
    http('POST', url, payload, callback);
}

function http(method, url, payload, callback) {
    const xhr = new XMLHttpRequest();
    xhr.withCredentials = true;
    xhr.open(method, url, true);
    xhr.setRequestHeader('Content-type', 'application/json');
    xhr.onreadystatechange = function () {
        if (xhr.readyState === XMLHttpRequest.DONE) {
            const response = JSON.parse(xhr.responseText);
            callback(xhr.status, response);
        }
    };
    xhr.send(JSON.stringify(payload));
}

// 简化的本地模拟响应
function simulateResponse(method, url, payload, callback) {
    console.log(`LOCAL SIMULATION - ${method} ${url}:`, payload);
    
    // 模拟延迟
    setTimeout(() => {
        if (url === '/userinfo') {
            // 模拟用户信息响应
            if (window.playerInfo) {
                callback(200, window.playerInfo);
            } else {
                callback(404, { detail: 'User not found' });
            }
        } else if (url === '/login') {
            // 模拟登录响应
            const playerInfo = {
                uid: 1,
                name: payload.name || "本地玩家",
                point: 1000,
                room: -1,
                rooms: [{ level: 1, number: 1 }]
            };
            window.playerInfo = playerInfo;
            callback(200, playerInfo);
        } else {
            // 默认响应
            callback(404, { detail: 'Not found' });
        }
    }, 200);
}

// 本地初始化玩家信息
function initLocalPlayer(name) {
    return {
        uid: 1,
        name: name || "本地玩家",
        point: 1000,
        room: -1
    };
}

// 设置是否使用本地模拟模式
window.USE_LOCAL_SIMULATION = false;

export class Boot {
    preload() {
        this.load.image('preloaderBar', 'static/i/preload.png');
    }

    create() {
        this.input.maxPointers = 1;
        this.stage.disableVisibilityChange = true;
        this.scale.scaleMode = Phaser.ScaleManager.SHOW_ALL;
        this.scale.enterIncorrectOrientation.add(this.enterIncorrectOrientation, this);
        this.scale.leaveIncorrectOrientation.add(this.leaveIncorrectOrientation, this);
        this.onSizeChange();
        
        // 初始化音乐设置
        if (localStorage.getItem('musicEnabled') === null) {
            localStorage.setItem('musicEnabled', 'true');
        }
        
        this.state.start('Preloader');
    }

    onSizeChange() {
        this.scale.minWidth = 480;
        this.scale.minHeight = 270;
        let device = this.game.device;
        if (device.android || device.iOS) {
            this.scale.maxWidth = window.innerWidth;
            this.scale.maxHeight = window.innerHeight;
        } else {
            this.scale.maxWidth = 960;
            this.scale.maxHeight = 540;
        }
        this.scale.pageAlignHorizontally = true;
        this.scale.pageAlignVertically = true;
        this.scale.forceOrientation(true);
    }

    enterIncorrectOrientation() {
        // orientated = false;
        document.getElementById('orientation').style.display = 'block';
    }

    leaveIncorrectOrientation() {
        // orientated = true;
        document.getElementById('orientation').style.display = 'none';
    }
}

export class Preloader {

    preload() {
        this.preloadBar = this.game.add.sprite(120, 200, 'preloaderBar');
        this.load.setPreloadSprite(this.preloadBar);

        this.load.audio('music_room', 'static/audio/bg_room.mp3');
        this.load.audio('music_game', 'static/audio/bg_game.ogg');
        this.load.audio('music_deal', 'static/audio/deal.mp3');
        this.load.audio('music_win', 'static/audio/end_win.mp3');
        this.load.audio('music_lose', 'static/audio/end_lose.mp3');
        this.load.audio('f_score_0', 'static/audio/f_score_0.mp3');
        this.load.audio('f_score_1', 'static/audio/f_score_1.mp3');
        this.load.atlas('btn', 'static/i/btn.png', 'static/i/btn.json');
        this.load.image('bg', 'static/i/bg.png');
        this.load.spritesheet('poker', 'static/i/poker.png', 90, 120);
        this.load.json('rule', 'static/rule.json');
    }

    create() {
        const that = this;
        
        // 根据音乐设置控制背景音乐
        const musicEnabled = localStorage.getItem('musicEnabled') === 'true';
        this.game.sound.mute = !musicEnabled;
        
        if (window.USE_LOCAL_SIMULATION) {
            // 本地初始化玩家信息
            window.playerInfo = initLocalPlayer("本地玩家");
            that.state.start('MainMenu');
        } else {
            // 通过网络请求获取玩家信息
            get('/userinfo', {}, function (status, response) {
                if (status === 200) {
                    window.playerInfo = response;
                    if (response['uid']) {
                        that.state.start('MainMenu');
                    } else {
                        that.state.start('Login');
                    }
                } else {
                    that.state.start('Login');
                }
            });
        }
        
        const music = this.game.add.audio('music_room');
        music.loop = true;
        music.loopFull();
        music.play();
    }
}

export class MainMenu {
    create() {
        this.stage.backgroundColor = '#182d3b';
        let bg = this.game.add.sprite(this.game.width / 2, 0, 'bg');
        bg.anchor.set(0.5, 0);

        let aiRoom = this.game.add.button(this.game.world.width / 2, this.game.world.height / 3, 'btn', this.gotoAiRoom, this, 'quick.png', 'quick.png', 'quick.png');
        aiRoom.anchor.set(0.5);
        this.game.world.add(aiRoom);

        let setting = this.game.add.button(this.game.world.width / 2, this.game.world.height * 2 / 3, 'btn', this.gotoSetting, this, 'setting.png', 'setting.png', 'setting.png');
        setting.anchor.set(0.5);
        this.game.world.add(setting);

        let style = {font: "28px Arial", fill: "#fff", align: "right"};
        let text = this.game.add.text(this.game.world.width - 4, 4, "欢迎回来 " + window.playerInfo.name, style);
        text.addColor('#cc00cc', 4);
        text.anchor.set(1, 0);
        
        // 添加音乐开关按钮
        // 从localStorage读取音乐设置，默认为开启
        if (localStorage.getItem('musicEnabled') === null) {
            localStorage.setItem('musicEnabled', 'true');
        }
        const musicEnabled = localStorage.getItem('musicEnabled') === 'true';
        
        // 创建音乐按钮样式和背景
        let musicBtnBg = this.game.add.graphics(0, 0);
        musicBtnBg.beginFill(0x4CAF50, 1);
        musicBtnBg.drawRoundedRect(0, 0, 200, 50, 10);
        musicBtnBg.endFill();
        
        let musicBtnStyle = {font: "24px Arial", fill: "#ffffff", align: "center"};
        let musicBtnText = musicEnabled ? "音乐: 开启" : "音乐: 关闭";
        
        // 创建音乐按钮
        let musicBtn = this.game.add.text(0, 0, musicBtnText, musicBtnStyle);
        musicBtn.anchor.set(0.5);
        
        // 创建一个组合按钮
        let musicBtnGroup = this.game.add.group();
        musicBtnGroup.add(musicBtnBg);
        musicBtnGroup.add(musicBtn);
        
        // 设置按钮位置
        musicBtnGroup.x = this.game.world.width / 2;
        musicBtnGroup.y = this.game.world.height * 0.5;
        musicBtn.x = musicBtnBg.width / 2;
        musicBtn.y = musicBtnBg.height / 2;
        
        // 使按钮可点击
        musicBtnBg.inputEnabled = true;
        musicBtnBg.events.onInputDown.add(() => {
            // 切换音乐状态
            const newMusicEnabled = !(localStorage.getItem('musicEnabled') === 'true');
            localStorage.setItem('musicEnabled', newMusicEnabled);
            
            // 更新按钮文本
            musicBtn.text = newMusicEnabled ? "音乐: 开启" : "音乐: 关闭";
            
            // 控制背景音乐
            if (newMusicEnabled) {
                if (this.game.sound.mute) {
                    this.game.sound.mute = false;
                }
            } else {
                if (!this.game.sound.mute) {
                    this.game.sound.mute = true;
                }
            }
        }, this);

        let infoStyle = {font: "24px Arial", fill: "#fff", align: "center"};
        let infoText = this.game.add.text(this.game.world.width / 2, this.game.world.height - 40, "单机版：仅支持人机对战", infoStyle);
        infoText.anchor.set(0.5);

        // 根据设置控制背景音乐
        this.game.sound.mute = !musicEnabled;

        // this.state.start('Game', true, false, 1);
    }

    gotoAiRoom() {
        // 停止背景音乐
        this.game.sound.stopAll();
        
        // start(key, clearWorld, clearCache, parameter)
        this.state.start('Game', true, false, 1);
    }

    gotoRoom() {
        // 保留方法但不使用
        // this.state.start('Game', true, false, 2);
    }

    gotoSetting() {
        let style = {font: "22px Arial", fill: "#fff", align: "center"};
        let text = this.game.add.text(0, 0, "hei hei hei hei", style);
        let tween = this.game.add.tween(text).to({x: 600, y: 450}, 2000, "Linear", true);
        tween.onComplete.add(Phaser.Text.prototype.destroy, text);
    }
}

export class Login {
    create() {
        this.stage.backgroundColor = '#182d3b';
        let bg = this.game.add.sprite(this.game.width / 2, 0, 'bg');
        bg.anchor.set(0.5, 0);

        this.game.add.plugin(PhaserInput.Plugin);
        const style = {
            font: '32px Arial', fill: '#000', width: 300, padding: 12,
            borderWidth: 1, borderColor: '#c8c8c8', borderRadius: 2,
            textAlign: 'center', placeHolder: '请输入用户名'
        };
        this.name = this.game.add.inputField((this.game.world.width - 300) / 2, this.game.world.centerY - 40, style);

        this.errorText = this.game.add.text(this.game.world.centerX, this.game.world.centerY + 24, '', {
            font: "24px Arial",
            fill: "#f00",
            align: "center"
        });
        this.errorText.anchor.set(0.5, 0);

        let login = this.game.add.button(this.game.world.centerX, this.game.world.centerY + 100, 'btn', this.onLogin, this, 'login.png', 'login.png', 'login.png');
        login.anchor.set(0.5);
    }

    onLogin() {
        this.errorText.text = '';
        if (!this.name.value) {
            this.name.startFocus();
            this.errorText.text = '请输入用户名';
            return;
        }
        
        if (window.USE_LOCAL_SIMULATION) {
            // 本地初始化玩家信息
            window.playerInfo = initLocalPlayer(this.name.value);
            this.state.start('MainMenu');
        } else {
            // 通过网络请求登录
            let that = this;
            const payload = {
                "name": this.name.value,
            };
            post('/login', payload, function (status, response) {
                if (status === 200) {
                    window.playerInfo = response;
                    that.state.start('MainMenu');
                } else {
                    that.errorText.text = response.detail;
                }
            });
        }
    }
}