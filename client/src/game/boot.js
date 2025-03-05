import Phaser from "phaser";
import { store, subscribe, TOGGLE_MUSIC } from './store';

let PG = {
    music: null,
    playerInfo: {
        username: "玩家"
    },
    orientated: false
};

class BootScene extends Phaser.Scene {

    constructor() {
        super('BootScene')
    }

    preload() {
        this.load.audio('music_game', 'assets/audio/bg_game.ogg');
        this.load.audio('music_room', 'assets/audio/bg_room.mp3');
        this.load.audio('music_deal', 'assets/audio/deal.mp3');
        this.load.audio('music_win',  'assets/audio/end_win.mp3');
        this.load.audio('music_lose', 'assets/audio/end_lose.mp3');
        this.load.audio('f_score_0', 'assets/audio/f_score_0.mp3');
        this.load.audio('f_score_1', 'assets/audio/f_score_1.mp3');
        this.load.audio('f_score_2', 'assets/audio/f_score_2.mp3');
        this.load.audio('f_score_3', 'assets/audio/f_score_3.mp3');
        this.load.multiatlas('ui', 'assets/ui.json', 'assets');
        this.load.image('bg', 'assets/bg.png');
        this.load.spritesheet('poker', 'assets/poker.png', {
            frameWidth: 90,
            frameHeight: 120
        });
        this.load.json('rule', 'assets/rule.json');
    }

    create() {
        console.log("BootScene create method called!");
        // 加载菜单背景音乐
        PG.music = this.sound.add('music_room');
        PG.music.loop = true;
        
        // 根据设置决定是否播放音乐
        const musicEnabled = store.getState().settings.musicEnabled;
        if (musicEnabled) {
            PG.music.play();
        }
        
        // 切换到菜单场景
        this.scene.start('MenuScene');
    }
}

class MenuScene extends Phaser.Scene {

    constructor() {
        super('MenuScene')
    }

    create() {
        console.log("MenuScene create method called!");
        this.backgroundColor = '#182d3b';
        let bg = this.add.sprite(this.game.config.width / 2, 0, 'bg');
        bg.setOrigin(0.5, 0);

        const self = this;
        let aiRoom = this.add.sprite(this.game.config.width / 2, this.game.config.height / 3, 'ui', 'quick.png');
        aiRoom.setInteractive().on('pointerup', () => this.gotoAiRoom());

        let setting = this.add.sprite(this.game.config.width / 2, this.game.config.height * 2 / 3, 'ui', 'setting.png');
        setting.setOrigin(0.5);
        setting.setInteractive().on('pointerup', () => this.gotoSetting());

        let style = {fontSize: "28px", backgroundColor: "#f0f0f0", color: "#333", align: "left"};
        let text = this.add.text(15, 10, "欢迎回来 " + PG.playerInfo.username, style);
        text.setOrigin(0, 0);
        
        // 添加音乐开关按钮
        let musicBtnStyle = {
            fontSize: "28px", 
            backgroundColor: "#4CAF50", 
            color: "#fff", 
            align: "center", 
            padding: {x: 20, y: 10},
            fixedWidth: 200
        };
        
        // 获取当前音乐状态
        const musicEnabled = store.getState().settings.musicEnabled;
        let musicBtnText = musicEnabled ? "音乐: 开启" : "音乐: 关闭";
        
        // 将音乐按钮放在更明显的位置
        let musicBtn = this.add.text(
            this.game.config.width / 2, 
            this.game.config.height * 0.4, 
            musicBtnText, 
            musicBtnStyle
        );
        musicBtn.setOrigin(0.5);
        musicBtn.setInteractive();
        
        // 点击切换音乐状态
        musicBtn.on('pointerup', () => {
            store.dispatch({ type: TOGGLE_MUSIC });
            const newMusicEnabled = store.getState().settings.musicEnabled;
            musicBtn.setText(newMusicEnabled ? "音乐: 开启" : "音乐: 关闭");
            
            // 如果开启音乐，立即播放背景音乐
            if (newMusicEnabled && PG.music) {
                PG.music.play();
            } else if (!newMusicEnabled && PG.music) {
                PG.music.stop();
            }
        });
        
        let infoStyle = {fontSize: "24px", color: "#fff", align: "center"};
        let infoText = this.add.text(this.game.config.width / 2, this.game.config.height - 40, "单机版：仅支持人机对战", infoStyle);
        infoText.setOrigin(0.5);
    }

    gotoAiRoom() {
        // 停止菜单背景音乐
        if (PG.music && PG.music.isPlaying) {
            PG.music.stop();
        }
        this.scene.start('GameScene');
    }

    gotoRoom() {
        // 停止菜单背景音乐
        if (PG.music && PG.music.isPlaying) {
            PG.music.stop();
        }
        this.scene.start('GameScene');
    }

    gotoSetting() {
        let style = {fontSize: "22px", color: "#fff", align: "center"};
        let text = this.add.text(0, 0, "设置页面", style);
        
        // 使用Phaser 3的补间动画API
        this.tweens.add({
            targets: text,
            x: 600,
            y: 450,
            duration: 2000,
            ease: 'Linear',
            onComplete: () => {
                text.destroy();
            }
        });
    }
}

export {BootScene, MenuScene}