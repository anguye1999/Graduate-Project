import React from 'react';
import '../styles/Page.css';

const Page = () => (
  <main className="main-content">
    <div className="content-container">
      <img 
        src="https://shadygrove.umd.edu/sites/default/files/styles/max_2600x2600/public/u75/academic-partner/logo/TowsonUlogo-horiz-color-pos.png?itok=ef6nkIML"
        alt="Towson University Logo"
        className="logo"
      />
      <h2 className="welcome-text">
        Welcome to Towson Pathways!
      </h2>

      <a href="https://www.towson.edu/">
        <button class="home-button">
          Home
        </button>
      </a>

      <a href="https://www.towson.edu/academics/resources/courses.html">
        <button class="catalog-button">
          Towson Course Catalog
        </button>
      </a>
    </div>
  </main>
);

export default Page;