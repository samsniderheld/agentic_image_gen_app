export default function VideoBubble({ message }) {
  const handleDownload = () => {
    const link = document.createElement('a');
    link.href = message.src;
    link.download = 'generated_video.mp4';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleError = (e) => {
    console.error('Video error:', e);
    console.error('Video src:', message.src);
  };

  const handleLoadStart = () => {
    console.log('Video loading started:', message.src);
  };

  const handleCanPlay = () => {
    console.log('Video can play:', message.src);
  };

  return (
    <div className="video-bubble">
      <video
        src={message.src}
        controls
        className="video-player"
        preload="metadata"
        onError={handleError}
        onLoadStart={handleLoadStart}
        onCanPlay={handleCanPlay}
      >
        Your browser does not support the video tag.
      </video>
      {message.caption && <div className="video-caption">{message.caption}</div>}
      <button className="video-download" onClick={handleDownload}>
        Download Video
      </button>
    </div>
  );
}
