import {useState, useRef} from 'react'
import './uploader.css';


function Uploader() {
    const [imageFile, setImageFile] = useState(null);
    const [textFile, setTextFile] = useState(null);
    const imageInputRef = useRef(null);
  
    const handleImageUpload = (event) => {
      let file = event.target.files[0];
      if (file && (file.type === "image/jpeg" || file.type === "image/jpg")) {
          setImageFile(event.target.files[0]);
      } else {
          alert("Invalid file type. Please select a JPEG or JPG image.");
      }
  };
  
  const handleTextUpload = (event) => {
      let file = event.target.files[0];
      if (file && (file.type === "text/plain")) {
          setTextFile(event.target.files[0]);
      } else {
          alert("Invalid file type. Please select a text file.");
      }
  };
  
  return (
      <div className="root">
          <div className="image-uploader">
              <input
                  type="file"
                  style={{ display: 'none' }}
                  ref={imageInputRef}
                  onChange={handleImageUpload}
                  accept="image/jpeg, image/jpg"
              />
              <button onClick={() => imageInputRef.current.click()}>Upload Image</button>
              {imageFile && <img src={URL.createObjectURL(imageFile)} alt="Preview" />}
          </div>
        <div className="text-uploader">
            <input
            type="file"
            label="Upload Text"
            variant="outlined"
            fullWidth
            onChange={handleTextUpload}
            accept=".txt"
            />
          {textFile && <p>{textFile.name}</p>}
        </div>
      </div>
    );
  }
  
  export default Uploader;