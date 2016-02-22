module.exports = function(grunt) {

  grunt.initConfig({
    pkg: grunt.file.readJSON('package.json'),

    // Sass: Compiles .scss files and saves them as .css
    sass: {
      options: {
        includePaths: ['bower_components/foundation/scss'],
      },
      dev: {
        options: {
          outputStyle: 'nested',
          imagePath: '/assets/img'
        },
        files: {
          'static/css/app.css': 'src/scss/app.scss'
        }
      },
      deploy: {
        options: {
          outputStyle: 'compressed',
          imagePath: '/static/assets/img'
        },
        files: {
          'static/css/app.css': 'src/scss/app.scss'
        }
      }
    },

    // CSS Autorpefix https://github.com/postcss/autoprefixer
    postcss: {
      options: {
        map: true,
        processors: [
          require('autoprefixer-core')({browsers: 'last 1 version'}),
          require('csswring').postcss
        ]
      },
      dist: {
        src: 'static/css/app.css'
      }
    },

    // Assemble: Compiles .hbs files and saves them as .html
    assemble: {
      options: {
        layoutdir: 'src/layout/',
        layout: 'default.hbs',
        data: 'src/data/*.json',
        flatten: true
      },
      pages: {
        options:{
          partials: ['src/partial/**/*.hbs']
        },
        files: {
          'static/': ['src/page/*.hbs']
        }
      }
    },

    // Imagemin: Minifies and copies images
    imagemin: {
      main: {
        files: [{
          expand: true,
          cwd: 'src/assets/img',
          src: ['**/*.{png,jpg}'], // GIFs are copied manually
          dest: 'static/assets/img'
        }]
      },
    },

    // SVG Store for vector icons
    svgstore: {
      options: {
        prefix : 'icon-', // This will prefix each ID
        cleanup: true,
        svg: { // will add and overide the the default xmlns="http://www.w3.org/2000/svg" attribute to the resulting SVG
          style: "display: none;"
        }
      },
      dist: {
        files: {
          'src/partial/svg_icons.hbs': ['src/assets/icons/*.svg']
        }
      },
    },


    // Foundation scripts
    // 1 file to rule them all! (just choose what you always need)
    concat: {
      options: {
        separator: ';\n'
      },
      dist: {
        src: [
          'bower_components/foundation/js/foundation/foundation.js',
          // 'bower_components/foundation/js/foundation/foundation.abide.js',
          'bower_components/foundation/js/foundation/foundation.accordion.js',
          // 'bower_components/foundation/js/foundation/foundation.alert.js',
          'bower_components/foundation/js/foundation/foundation.clearing.js',
          'bower_components/foundation/js/foundation/foundation.dropdown.js',
          'bower_components/foundation/js/foundation/foundation.equalizer.js',
          'bower_components/foundation/js/foundation/foundation.interchange.js',
          // 'bower_components/foundation/js/foundation/foundation.joyride.js',
          // 'bower_components/foundation/js/foundation/foundation.magellan.js',
          'bower_components/foundation/js/foundation/foundation.offcanvas.js',
          // 'bower_components/foundation/js/foundation/foundation.orbit.js',
          // 'bower_components/foundation/js/foundation/foundation.reveal.js',
          // 'bower_components/foundation/js/foundation/foundation.slider.js',
          'bower_components/foundation/js/foundation/foundation.tab.js',
          'bower_components/foundation/js/foundation/foundation.tooltip.js',
          'bower_components/foundation/js/foundation/foundation.topbar.js'
        ],
        dest: 'src/js/foundation.js',
      },
      app: {
        src: [
          'src/js/app.js',
          'src/js/filter.js'
        ],
        dest: 'static/js/main.js',
      },
    },
    // Make it smaller
    uglify: {
      options: {
        mangle: false
      },
      dist: {
        files: {
          'static/js/foundation.min.js': ['src/js/foundation.js']
        }
      },
      app: {
        files: {
          'static/js/main.min.js': ['static/js/main.js']
        }
      },
      wizard: {
        files: {
          'static/js/wizard.min.js': ['src/js/wizard.js']
        }
      }
    },

    // Copy: copies files (libraries and single files, e.g. fonts)
    copy: {
      main: {
        files: [{
          'static/js/modernizr.js': 'bower_components/modernizr/modernizr.js',
          'static/js/jquery.min.js': 'bower_components/jquery/dist/jquery.min.js',
          'static/js/jquery.min.map': 'bower_components/jquery/dist/jquery.min.map',
          'static/js/jquery-ui.min.js': 'bower_components/jquery-ui/jquery-ui.min.js',
          'static/js/jquery.nstSlider.min.js': 'bower_components/jquery-nstSlider/dist/jquery.nstSlider.min.js',
          'static/js/dropzone.min.js': 'bower_components/dropzone/dist/min/dropzone.min.js',
          'static/js/app.js': 'src/js/app.js',
          'static/js/filter.js': 'src/js/filter.js',
          'static/js/parallax.js': 'src/js/parallax.js',
          'static/js/wocat.magellan.js': 'src/js/wocat.magellan.js',
          'static/js/wizard.js': 'src/js/wizard.js',
          'static/js/chosen.jquery.min.js': 'bower_components/chosen/chosen.jquery.min.js',
          'static/css/chosen.min.css': 'bower_components/chosen/chosen.min.css',
          'static/css/chosen-sprite.png': 'bower_components/chosen/chosen-sprite.png'
        }
        ,{
          expand: true,
          cwd: 'bower_components/foundation/js/foundation/',
          src: ['**/*'],
          dest: 'static/js/foundation/'
        }
        // Manually copy GIFs
        ,{
          expand: true,
          cwd: 'src/assets/img/',
          src: ['*.gif'],
          dest: 'static/assets/img/'
        }
        ]
      },
      assets: {
        files: [{
          expand: true,
          cwd: 'src/assets/files',
          src: ['**/*'],
          dest: 'static/assets/files'
        },{
          expand: true,
          cwd: 'src/assets/fonts',
          src: ['**/*'],
          dest: 'static/assets/fonts'
        },{
          // Copy svg
          expand: true,
          cwd: 'src/assets/img',
          src: ['*.svg'],
          dest: 'static/assets/img'
        }]
      }
    },

    // Watch: check for changes and reload web browser
    watch: {
      sass: {
        files: 'src/scss/**/*.scss',
        tasks: ['sass:dev', 'postcss'],
        options: {
          livereload: true,
        }
      },
      assets: {
        files: 'src/assets/**/*',
        tasks: ['copy', 'imagemin'],
        options: {
          livereload: true,
        }
      },
      js: {
        files: 'src/js/**/*.js',
        tasks: ['concat', 'uglify', 'copy'],
        options: {
          livereload: true,
        }
      },
      html: {
        files: ['src/**/*.hbs', 'src/embed/**/*'],
        tasks: ['assemble'],
        options: {
          livereload: true,
        }
      },
      data: {
        files: 'src/data/*.json',
        tasks: ['assemble'],
        options: {
          livereload: true,
        }
      }
    },

    // Connect: Grunt server
    connect: {
      server: {
        options: {
          hostname: '0.0.0.0',
          port: 8000,
          livereload: true,
          open: true,
          base: 'static'
        }
      }
    }
  });

  grunt.loadNpmTasks('assemble');
  grunt.loadNpmTasks('grunt-sass');
  grunt.loadNpmTasks('grunt-postcss');
  grunt.loadNpmTasks('grunt-contrib-concat');
  grunt.loadNpmTasks('grunt-contrib-uglify');
  grunt.loadNpmTasks('grunt-contrib-copy');
  grunt.loadNpmTasks('grunt-contrib-watch');
  grunt.loadNpmTasks('grunt-contrib-connect');
  grunt.loadNpmTasks('grunt-contrib-imagemin');
  grunt.loadNpmTasks('grunt-svgstore');

  /**
   * Available commands:
   * IMPORTANT: Update the documentation if you edit or add commands.
   * grunt                : Build (uncompressed) and run the server
   * grunt build          : Build (uncompressed)
   * grunt build:deploy   : Build (compressed)
   * grunt server         : Run the server
   */
  grunt.registerTask('build', function(arg) {
    // Default mode is 'dev'
    var mode = (arg && arg === 'deploy') ? 'deploy' : 'dev';
    grunt.task.run(['sass:' + mode, 'svgstore', 'imagemin', 'concat', 'uglify', 'copy', 'assemble']);
  });
  grunt.registerTask('server', ['connect:server', 'watch']);
  grunt.registerTask('default', ['build', 'server']);
}
