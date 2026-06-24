"""Day image preview/PDF styles."""

CSS = r"""
.day-visual-block {
            margin: auto -64px -66px -64px;
            flex: 0 0 auto;
        }


        .day-image-slot {
            margin: 0;
            height: 410px;
            overflow: visible;
            flex: 0 0 410px;
            position: relative;
            border-top: 5px solid rgba(184,149,85,.96);
            box-shadow: none;
            box-sizing: border-box;
        }

        .day-image-slot::before {
            content: "";
            position: absolute;
            left: 0;
            right: 0;
            top: 0;
            height: 26px;
            background: linear-gradient(to bottom, rgba(244,239,232,.16), rgba(244,239,232,0));
            z-index: 1;
            pointer-events: none;
        }

        .day-image-preview-img {
            display: block;
            width: 100%;
            height: 100%;
            object-fit: cover;
            object-position: center 25%;
        }
"""
