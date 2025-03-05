import React from 'react';
import {Login, } from './components/Login'
import Game from './game/Index'

class App extends React.Component {

	constructor(props) {
		super(props);

		const token = localStorage.getItem('token');
		this.state = {
			token: token,
			page: !!token ? 'game' : 'login',
		}
	}

	onChange(page, response) {
		this.setState({'page': page, 'token': response});
	}

	render() {
		switch (this.state.page) {
			case 'login':
                return <div><Login onChange={(page, response) => this.onChange(page, response)}/></div>;
			case "game":
            default:
                return <Game onChange={(page, response) => this.onChange(page, response)}/>;
		}
	}
}

export default App;
