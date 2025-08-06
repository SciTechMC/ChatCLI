import React, { useRef, useState, useEffect } from 'react'
import SimplePeer from 'simple-peer'

const SIGNALING_SERVER = 'ws://127.0.0.1:8765/ip/call'
const USERNAME = prompt('Your username') || 'user-' + Math.floor(Math.random() * 1000)
const PEERNAME = prompt('Who do you want to call?') || ''

let socket
let peer

export default function CallComponent() {
  const [inCall, setInCall] = useState(false)
  const remoteAudioRef = useRef(null)

  const connectWebSocket = () => {
    socket = new WebSocket(`${SIGNALING_SERVER}/${USERNAME}`)

    socket.onmessage = async (event) => {
      const message = JSON.parse(event.data)
      const { type, data, from } = message

      if (type === 'call-offer') {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
        peer = new SimplePeer({ initiator: false, trickle: false, stream })

        peer.on('signal', (answerSignal) => {
          socket.send(JSON.stringify({
            type: 'call-answer',
            to: from,
            data: answerSignal
          }))
        })

        peer.on('stream', (remoteStream) => {
          if (remoteAudioRef.current) {
            remoteAudioRef.current.srcObject = remoteStream
            remoteAudioRef.current.play()
          }
        })

        peer.signal(data)
        setInCall(true)
      }

      if (type === 'call-answer') {
        peer.signal(data)
      }
    }
  }

  const startCall = async () => {
    connectWebSocket()

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    peer = new SimplePeer({ initiator: true, trickle: false, stream })

    peer.on('signal', (offerSignal) => {
      socket.send(JSON.stringify({
        type: 'call-offer',
        to: PEERNAME,
        data: offerSignal
      }))
    })

    peer.on('stream', (remoteStream) => {
      if (remoteAudioRef.current) {
        remoteAudioRef.current.srcObject = remoteStream
        remoteAudioRef.current.play()
      }
    })

    setInCall(true)
  }

  const endCall = () => {
    if (peer) peer.destroy()
    if (socket) socket.close()
    setInCall(false)
  }

  return React.createElement(
    'div',
    null,
    React.createElement('h2', null, 'Call MVP'),
    !inCall &&
      React.createElement(
        'button',
        {
          className: 'call-button',
          onClick: startCall
        },
        '📞 Call'
      ),
    inCall &&
      React.createElement(
        'button',
        {
          className: 'call-button',
          onClick: endCall
        },
        '❌ End Call'
      ),
    React.createElement('audio', {
      ref: remoteAudioRef,
      autoPlay: true
    })
  )
}
