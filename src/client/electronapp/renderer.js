import {
  login,
  register,
  verifyEmail,
  fetchChats
} from './api.js';

let sessionToken = null;
let currentUser = null;

document.addEventListener('DOMContentLoaded', () => {
  const page = window.location.pathname.split('/').pop();

  if (page === 'index.html') {
    document.getElementById('btnLogin').onclick = () =>
      window.location.href = 'pages/login.html';
    document.getElementById('btnRegister').onclick = () =>
      window.location.href = 'pages/register.html';
  }

  if (page === 'login.html') {
    document.getElementById('loginForm').onsubmit = async e => {
      e.preventDefault();
      const username = e.target.username.value;
      const password = e.target.password.value;
      try {
        const res = await window.api.login({ username, password });
        sessionToken = res.token;
        currentUser = username;
        window.location.href = 'pages/main.html';
      } catch (err) {
        alert(err.message);
      }
    };
  }

  if (page === 'register.html') {
    document.getElementById('registerForm').onsubmit = async e => {
      e.preventDefault();
      const data = {
        username: e.target.regUsername.value,
        email: e.target.regEmail.value,
        password: e.target.regPassword.value
      };
      try {
        await window.api.register(data);
        window.location.href = 'pages/verify.html';
      } catch (err) {
        alert(err.message);
      }
    };
  }

  if (page === 'verify.html') {
    document.getElementById('verifyForm').onsubmit = async e => {
      e.preventDefault();
      try {
        await window.api.verifyEmail({ token: e.target.token.value });
        window.location.href = 'pages/login.html';
      } catch (err) {
        alert(err.message);
      }
    };
  }

  if (page === 'main.html') {
    document.getElementById('btnSend').onclick = () => {
      // TODO: integrate WebSocket send
    };
    // Load chat list
    (async () => {
      try {
        const chats = await window.api.fetchChats(currentUser, sessionToken);
        // render chats...
      } catch (err) {
        console.error(err);
      }
    })();
  }
});