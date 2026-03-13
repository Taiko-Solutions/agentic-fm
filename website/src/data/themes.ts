export interface ThemeColors {
  comments: string;
  controlFlow: string;
  scriptSteps: string;
  variables: string;
  globals: string;
  fields: string;
  strings: string;
  functions: string;
  constants: string;
  numbers: string;
  operators: string;
  brackets: string;
}

export interface GalleryTheme {
  id: string;
  name: string;
  credit?: string;
  creditUrl?: string;
  colors: ThemeColors;
}

export const GALLERY_THEMES: GalleryTheme[] = [
  {
    id: 'monokai',
    name: 'Monokai',
    credit: 'Wimer Hazenberg',
    creditUrl: 'https://monokai.pro',
    colors: {
      comments: '#75715E',
      controlFlow: '#F92672',
      scriptSteps: '#66D9EF',
      variables: '#FD971F',
      globals: '#A6E22E',
      fields: '#E6DB74',
      strings: '#E6DB74',
      functions: '#A6E22E',
      constants: '#AE81FF',
      numbers: '#AE81FF',
      operators: '#F8F8F2',
      brackets: '#F8F8F2',
    },
  },
  {
    id: 'github_dark',
    name: 'GitHub Dark',
    credit: 'GitHub',
    colors: {
      comments: '#8B949E',
      controlFlow: '#FF7B72',
      scriptSteps: '#79C0FF',
      variables: '#FFA657',
      globals: '#3DC9B0',
      fields: '#E3B341',
      strings: '#A5D6FF',
      functions: '#D2A8FF',
      constants: '#79C0FF',
      numbers: '#79C0FF',
      operators: '#C9D1D9',
      brackets: '#C9D1D9',
    },
  },
  {
    id: 'ayu_dark',
    name: 'Ayu Dark',
    credit: 'dempfi',
    creditUrl: 'https://github.com/dempfi/ayu',
    colors: {
      comments: '#5C6773',
      controlFlow: '#F29718',
      scriptSteps: '#36A3D9',
      variables: '#F07178',
      globals: '#B8CC52',
      fields: '#E6B450',
      strings: '#B8CC52',
      functions: '#FFB454',
      constants: '#F07178',
      numbers: '#F07178',
      operators: '#E7E8E9',
      brackets: '#E6B450',
    },
  },
  {
    id: 'tomorrow_night',
    name: 'Tomorrow Night',
    credit: 'Chris Kempson',
    creditUrl: 'https://github.com/chriskempson/tomorrow-theme',
    colors: {
      comments: '#969896',
      controlFlow: '#CC6666',
      scriptSteps: '#81A2BE',
      variables: '#DE935F',
      globals: '#B5BD68',
      fields: '#F0C674',
      strings: '#B5BD68',
      functions: '#81A2BE',
      constants: '#B294BB',
      numbers: '#DE935F',
      operators: '#C5C8C6',
      brackets: '#F0C674',
    },
  },
  {
    id: 'clouds_midnight',
    name: 'Clouds Midnight',
    credit: 'Nik Kalyani',
    colors: {
      comments: '#595959',
      controlFlow: '#C9005B',
      scriptSteps: '#4A9FFF',
      variables: '#FF9D00',
      globals: '#3ADC5A',
      fields: '#FFEE80',
      strings: '#3ADC5A',
      functions: '#4A9FFF',
      constants: '#C9005B',
      numbers: '#FF628C',
      operators: '#E8E8E8',
      brackets: '#FFEE80',
    },
  },
  {
    id: 'solarized_dark',
    name: 'Solarized Dark',
    credit: 'Ethan Schoonover',
    creditUrl: 'https://ethanschoonover.com/solarized/',
    colors: {
      comments: '#586E75',
      controlFlow: '#859900',
      scriptSteps: '#268BD2',
      variables: '#B58900',
      globals: '#2AA198',
      fields: '#CB4B16',
      strings: '#2AA198',
      functions: '#268BD2',
      constants: '#D33682',
      numbers: '#D33682',
      operators: '#839496',
      brackets: '#657B83',
    },
  },
  {
    id: 'solarized_light',
    name: 'Solarized Light',
    credit: 'Ethan Schoonover',
    creditUrl: 'https://ethanschoonover.com/solarized/',
    colors: {
      comments: '#93A1A1',
      controlFlow: '#859900',
      scriptSteps: '#268BD2',
      variables: '#B58900',
      globals: '#2AA198',
      fields: '#CB4B16',
      strings: '#2AA198',
      functions: '#268BD2',
      constants: '#D33682',
      numbers: '#D33682',
      operators: '#657B83',
      brackets: '#073642',
    },
  },
  {
    id: 'dracula',
    name: 'Dracula',
    credit: 'Zeno Rocha',
    creditUrl: 'https://draculatheme.com',
    colors: {
      comments: '#6272A4',
      controlFlow: '#FF79C6',
      scriptSteps: '#8BE9FD',
      variables: '#FFB86C',
      globals: '#50FA7B',
      fields: '#F1FA8C',
      strings: '#F1FA8C',
      functions: '#50FA7B',
      constants: '#BD93F9',
      numbers: '#BD93F9',
      operators: '#F8F8F2',
      brackets: '#F8F8F2',
    },
  },
  {
    id: 'one_dark',
    name: 'One Dark',
    credit: 'Atom',
    colors: {
      comments: '#5C6370',
      controlFlow: '#C678DD',
      scriptSteps: '#61AFEF',
      variables: '#E06C75',
      globals: '#98C379',
      fields: '#E5C07B',
      strings: '#98C379',
      functions: '#61AFEF',
      constants: '#56B6C2',
      numbers: '#D19A66',
      operators: '#ABB2BF',
      brackets: '#E5C07B',
    },
  },
  {
    id: 'nord',
    name: 'Nord',
    credit: 'Arctic Ice Studio',
    creditUrl: 'https://www.nordtheme.com',
    colors: {
      comments: '#616E88',
      controlFlow: '#81A1C1',
      scriptSteps: '#88C0D0',
      variables: '#D8DEE9',
      globals: '#A3BE8C',
      fields: '#EBCB8B',
      strings: '#A3BE8C',
      functions: '#88C0D0',
      constants: '#B48EAD',
      numbers: '#B48EAD',
      operators: '#D8DEE9',
      brackets: '#EBCB8B',
    },
  },
];
