import React from 'react'
import './Login.css'
import { store, TOGGLE_MUSIC } from '../game/store'

// const cookie = function (name) {
// 	let r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
// 	return r ? r[1] : undefined;
// };

const post = function (url, data, callback) {
	let xhr = new XMLHttpRequest();
	xhr.open('POST', 'http://127.0.0.1:8080' + url, true);
	xhr.setRequestHeader('Content-type', 'application/json');
	// xhr.setRequestHeader('X-Csrftoken', cookie("_xsrf"));
	xhr.onreadystatechange = function () {
		if (xhr.readyState === XMLHttpRequest.DONE) {
            const response = JSON.parse(xhr.responseText);
			if (xhr.status === 200) {
				callback(response);
			} else {
				alert(response.detail);
			}
		}
	};
	xhr.send(JSON.stringify(data));
};

class Login extends React.Component {

	constructor(props) {
		super(props);
		this.state = {
			username: '1',
			password: '1',
			musicEnabled: localStorage.getItem('musicEnabled') !== 'false' // 从localStorage读取音乐设置
		};
		this.handleChange = this.handleChange.bind(this);
		this.handleSubmit = this.handleSubmit.bind(this);
		this.toggleMusic = this.toggleMusic.bind(this);
	}

	handleChange(event) {
		const target = event.target;
		const name = target.name;
		this.setState({[name]: event.target.value});
	}

	handleSubmit(event) {
		event.preventDefault();
		const data = {"username": this.state.username, "password": this.state.password};
		const self = this;
		post('/login', data, response => self.props.onChange("game", response));
	}

	toggleMusic() {
		// 切换音乐状态
		store.dispatch({ type: TOGGLE_MUSIC });
		// 更新组件状态
		this.setState({ 
			musicEnabled: localStorage.getItem('musicEnabled') !== 'false' 
		});
	}

	render() {
		return (
			<div className="content">
				<div className="login-head">
					登录 <span className="login-second" onClick={() => this.props.onClick("signup")}> 立即注册 </span>
				</div>
				<form onSubmit={this.handleSubmit}>
					<input type="text"
								 name="username"
								 value={this.state.username}
								 onChange={this.handleChange}
								 placeholder="账号" required/>
					<input type="password"
								 name="password"
								 value={this.state.password}
								 onChange={this.handleChange}
								 placeholder="密码" required/>
					
					{/* 添加音乐开关选项 */}
					<div className="music-toggle">
						<label>
							<input 
								type="checkbox" 
								checked={this.state.musicEnabled} 
								onChange={this.toggleMusic}
							/>
							开启背景音乐
						</label>
					</div>
					
					<input type="submit" className="submit" value="登录"/>
				</form>
			</div>
		)
	}

}

export {Login, };